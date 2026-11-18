"""LangGraph orchestration for job discovery, analysis, and human review."""

import asyncio
from pathlib import Path
from typing import Any

import aiosqlite
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.discovery_agent import JobDiscoveryAgent
from app.agents.jd_analysis_agent import JDAnalysisAgent, ParsedJDRequirements
from app.agents.job_search_state import JobSearchAppState
from app.agents.portal_discovery_agent import PortalDiscoveryAgent
from app.agents.resume_optimizer_agent import ResumeOptimizerAgent
from app.config import settings
from app.connectors.registry import PortalConnectorRegistry
from app.core.exceptions import JobAgentException, PortalConnectorError
from app.db.models.candidate import CandidateProfile
from app.db.models.job import Job, JobDescription, JobMatch
from app.db.models.job_profile import JobProfile
from app.db.models.resume import Resume, ResumeVersion
from app.documents.docx_generator import ATSDocxGenerator
from app.documents.pdf_generator import ATSPdfGenerator

MAX_WORKFLOW_ITERATIONS = 12
GRAPH_RECURSION_LIMIT = 32


class WorkflowStateError(JobAgentException):
    """Raised when a workflow request cannot be run or resumed safely."""


def _database_session(config: RunnableConfig) -> AsyncSession:
    configurable = config.get("configurable", {})
    db_session = configurable.get("db_session")
    if db_session is None:
        raise WorkflowStateError("A database session is required for this workflow.")
    return db_session


def _advance(state: JobSearchAppState, agent_name: str) -> dict[str, Any]:
    iteration_count = state.get("iteration_count", 0) + 1
    if iteration_count > MAX_WORKFLOW_ITERATIONS:
        raise WorkflowStateError(
            f"Workflow exceeded the maximum of {MAX_WORKFLOW_ITERATIONS} agent iterations."
        )
    return {
        "current_agent": agent_name,
        "agent_history": [*state.get("agent_history", []), agent_name],
        "iteration_count": iteration_count
    }


def _serialize_job(job: Job) -> dict[str, Any]:
    created_at = getattr(job, "created_at", None)
    return {
        "id": job.id,
        "portal_id": job.portal_id,
        "external_job_id": job.external_job_id,
        "title": job.title,
        "company_name": job.company_name,
        "location": job.location,
        "url": job.url,
        "employment_type": job.employment_type,
        "salary_range": job.salary_range,
        "posted_date": job.posted_date,
        "status": job.status,
        "created_at": created_at.isoformat() if created_at else None
    }


def _start_route(state: JobSearchAppState) -> str:
    mode = state.get("mode")
    if mode not in {"discover", "inspect", "analyze", "optimize"}:
        raise WorkflowStateError(f"Unsupported workflow mode: '{mode}'.")
    return {
        "discover": "discover_jobs",
        "inspect": "inspect_portal",
        "analyze": "analyze_jd",
        "optimize": "optimize_resume"
    }[mode]


async def _discover_jobs(
    state: JobSearchAppState,
    config: RunnableConfig
) -> dict[str, Any]:
    db = _database_session(config)
    profile_id = state.get("active_job_profile_id")
    if not profile_id:
        raise WorkflowStateError("Job discovery requires an active job profile ID.")
    profile = await db.get(JobProfile, profile_id)
    if not profile:
        raise WorkflowStateError(f"Job profile '{profile_id}' was not found.")

    jobs = await JobDiscoveryAgent.discover_jobs(profile, db)
    serialized_jobs = [_serialize_job(job) for job in jobs]
    updates = _advance(state, "job_discovery")
    updates["discovered_jobs"] = serialized_jobs
    if state.get("selected_job_id"):
        updates["selected_job_id"] = state["selected_job_id"]
    return updates


def _route_after_discovery(state: JobSearchAppState) -> str:
    return "analyze_jd" if state.get("selected_job_id") else "finalize"


async def _inspect_portal(
    state: JobSearchAppState
) -> dict[str, Any]:
    target_url = state.get("target_url")
    if not target_url:
        raise WorkflowStateError("Portal inspection requires a target URL.")
    report = await PortalDiscoveryAgent.inspect_url(target_url)
    updates = _advance(state, "portal_discovery")
    updates["current_portal_report"] = report.to_dict()
    return updates


async def _get_raw_jd(
    state: JobSearchAppState,
    config: RunnableConfig
) -> tuple[str, Job | None]:
    raw_jd_text = state.get("raw_jd_text", "").strip()
    if raw_jd_text:
        job_id = state.get("selected_job_id")
        job = await _database_session(config).get(Job, job_id) if job_id else None
        if job_id and not job:
            raise WorkflowStateError(f"Job '{job_id}' was not found.")
        return raw_jd_text, job

    job_id = state.get("selected_job_id")
    if not job_id:
        raise WorkflowStateError("JD analysis requires job description text or a selected job ID.")

    db = _database_session(config)
    job = await db.get(Job, job_id)
    if not job:
        raise WorkflowStateError(f"Job '{job_id}' was not found.")
    result = await db.execute(
        select(JobDescription).where(JobDescription.job_id == job_id)
    )
    description = result.scalar_one_or_none()
    if description and description.raw_description.strip():
        return description.raw_description, job

    connector = await PortalConnectorRegistry.resolve_for_url(job.url)
    raw_jd_text = await connector.extract_job_description(job.url)
    if not raw_jd_text or not raw_jd_text.strip():
        raise PortalConnectorError(
            f"No job description could be extracted for job '{job_id}'."
        )
    return raw_jd_text, job


async def _analyze_jd(
    state: JobSearchAppState,
    config: RunnableConfig
) -> dict[str, Any]:
    raw_jd_text, job = await _get_raw_jd(state, config)
    parsed = await JDAnalysisAgent.analyze_jd_text(raw_jd_text)
    updates = _advance(state, "jd_analysis")
    updates["analyzed_jd"] = parsed.model_dump()

    if job:
        db = _database_session(config)
        result = await db.execute(
            select(JobDescription).where(JobDescription.job_id == job.id)
        )
        description = result.scalar_one_or_none()
        if description:
            description.raw_description = raw_jd_text
            description.extracted_mandatory_skills = parsed.mandatory_skills
            description.extracted_optional_skills = parsed.optional_skills
            description.extracted_experience_years = parsed.experience_years
            description.extracted_responsibilities = parsed.responsibilities
            description.extracted_ats_keywords = parsed.ats_keywords
            description.extracted_interview_topics = parsed.interview_topics
        else:
            db.add(JobDescription(
                job_id=job.id,
                raw_description=raw_jd_text,
                extracted_mandatory_skills=parsed.mandatory_skills,
                extracted_optional_skills=parsed.optional_skills,
                extracted_experience_years=parsed.experience_years,
                extracted_responsibilities=parsed.responsibilities,
                extracted_ats_keywords=parsed.ats_keywords,
                extracted_interview_topics=parsed.interview_topics
            ))
        job.status = "PROCESSED"
        await db.commit()
    return updates


def _route_after_analysis(state: JobSearchAppState) -> str:
    if state.get("active_job_profile_id") and state.get("selected_job_id"):
        return "evaluate_match"
    if state.get("require_human_approval"):
        return "prepare_approval"
    return "finalize"


async def _evaluate_match(
    state: JobSearchAppState,
    config: RunnableConfig
) -> dict[str, Any]:
    db = _database_session(config)
    profile_id = state["active_job_profile_id"]
    job_id = state["selected_job_id"]
    profile = await db.get(JobProfile, profile_id)
    if not profile:
        raise WorkflowStateError(f"Job profile '{profile_id}' was not found.")
    candidate = await db.get(CandidateProfile, profile.candidate_profile_id)
    if not candidate:
        raise WorkflowStateError(
            f"Candidate profile '{profile.candidate_profile_id}' was not found."
        )

    requirements = ParsedJDRequirements.model_validate(state.get("analyzed_jd", {}))
    candidate_experience = JDAnalysisAgent.calculate_verified_experience_years(
        candidate.verified_experience
    )
    evaluation = JDAnalysisAgent.calculate_compatibility(
        candidate_skills=candidate.verified_skills,
        candidate_exp_years=candidate_experience,
        jd_requirements=requirements
    )

    result = await db.execute(
        select(JobMatch).where(
            JobMatch.job_id == job_id,
            JobMatch.job_profile_id == profile_id
        )
    )
    match_record = result.scalar_one_or_none()
    if match_record:
        match_record.overall_match_score = evaluation.overall_score
        match_record.skills_match_score = evaluation.skills_score
        match_record.experience_match_score = evaluation.experience_score
        match_record.matching_skills = evaluation.matching_skills
        match_record.missing_skills = evaluation.missing_skills
    else:
        match_record = JobMatch(
            job_id=job_id,
            job_profile_id=profile_id,
            overall_match_score=evaluation.overall_score,
            skills_match_score=evaluation.skills_score,
            experience_match_score=evaluation.experience_score,
            matching_skills=evaluation.matching_skills,
            missing_skills=evaluation.missing_skills
        )
        db.add(match_record)
    await db.commit()
    await db.refresh(match_record)

    match_result = {
        "job_id": job_id,
        "job_profile_id": profile_id,
        "overall_match_score": evaluation.overall_score,
        "skills_match_score": evaluation.skills_score,
        "experience_match_score": evaluation.experience_score,
        "matching_skills": evaluation.matching_skills,
        "missing_skills": evaluation.missing_skills
    }
    updates = _advance(state, "compatibility_evaluation")
    updates["compatibility_score"] = evaluation.overall_score
    updates["match_result"] = match_result
    return updates


def _route_after_match(state: JobSearchAppState) -> str:
    return "prepare_approval" if state.get("require_human_approval") else "finalize"


def _prepare_approval(state: JobSearchAppState) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "selected_job_id": state.get("selected_job_id"),
        "compatibility_score": state.get("compatibility_score")
    }
    report = state.get("current_portal_report")
    if report:
        summary["portal_name"] = report.get("portal_name")
    match = state.get("match_result")
    if match:
        summary["missing_skills"] = match.get("missing_skills", [])
    updates = _advance(state, "human_review")
    updates["approval_status"] = "AWAITING_REVIEW"
    updates["workflow_status"] = "AWAITING_REVIEW"
    updates["workflow_status"] = "AWAITING_REVIEW"
    updates["approval_summary"] = summary
    return updates


def _await_human_review(state: JobSearchAppState) -> dict[str, Any]:
    decision = interrupt({
        "type": "human_review_required",
        "session_id": state.get("session_id"),
        "summary": state.get("approval_summary", {}),
        "message": "Review this workflow result and approve or reject continuation."
    })
    if not isinstance(decision, dict) or decision.get("decision") not in {"approve", "reject"}:
        raise WorkflowStateError("Resume the workflow with decision 'approve' or 'reject'.")
    return {"approval_status": "APPROVED" if decision["decision"] == "approve" else "REJECTED"}


async def _optimize_resume(
    state: JobSearchAppState,
    config: RunnableConfig
) -> dict[str, Any]:
    db = _database_session(config)
    resume_id = state.get("resume_id")
    job_id = state.get("selected_job_id")
    if not resume_id or not job_id:
        raise WorkflowStateError(
            "Resume optimization requires resume_id and selected_job_id."
        )

    resume = await db.get(Resume, resume_id)
    if not resume:
        raise WorkflowStateError(f"Resume '{resume_id}' was not found.")
    job = await db.get(Job, job_id)
    if not job:
        raise WorkflowStateError(f"Job '{job_id}' was not found.")
    candidate = await db.get(CandidateProfile, resume.candidate_profile_id)
    if not candidate:
        raise WorkflowStateError(
            f"Candidate profile '{resume.candidate_profile_id}' was not found."
        )
    description_result = await db.execute(
        select(JobDescription).where(JobDescription.job_id == job_id)
    )
    description = description_result.scalar_one_or_none()
    if not description:
        raise WorkflowStateError(
            "The selected job description must be analyzed before optimization."
        )

    result = ResumeOptimizerAgent.optimize(
        candidate_profile=candidate,
        resume=resume,
        job=job,
        description=description
    )
    version = ResumeVersion(
        resume_id=resume_id,
        job_id=job_id,
        version_label=f"{job.company_name} - {job.title}",
        tailored_text=result.tailored_text,
        tailored_json=result.tailored_json,
        ats_score=result.ats_score,
        grounding_verified=result.grounding_report.verified
    )
    db.add(version)
    await db.flush()

    pdf_path = f"{settings.RESUME_STORAGE_DIR}/ver_{version.id}.pdf"
    docx_path = f"{settings.RESUME_STORAGE_DIR}/ver_{version.id}.docx"
    ATSPdfGenerator.generate_pdf(result.tailored_json, pdf_path)
    ATSDocxGenerator.generate_docx(result.tailored_json, docx_path)
    version.pdf_file_path = pdf_path
    version.docx_file_path = docx_path
    await db.commit()
    await db.refresh(version)

    updates = _advance(state, "resume_optimizer")
    updates["active_resume_version_id"] = version.id
    updates["tailored_resume_data"] = result.tailored_json
    updates["grounding_verified"] = result.grounding_report.verified
    updates["generated_pdf_path"] = pdf_path
    updates["generated_docx_path"] = docx_path
    updates["approval_summary"] = {
        "resume_version_id": version.id,
        "ats_score": result.ats_score,
        "grounding_verified": result.grounding_report.verified
    }
    return updates


def _route_after_resume_optimizer(state: JobSearchAppState) -> str:
    return "prepare_approval" if state.get("require_human_approval") else "finalize"


def _finalize(state: JobSearchAppState) -> dict[str, Any]:
    updates = _advance(state, "workflow_complete")
    updates["workflow_status"] = (
        "REJECTED"
        if state.get("approval_status") == "REJECTED"
        else "COMPLETED"
    )
    return updates


def build_workflow_graph(checkpointer):
    """Builds the graph with an injected checkpointer for runtime and test use."""
    graph = StateGraph(JobSearchAppState)
    graph.add_node("discover_jobs", _discover_jobs)
    graph.add_node("inspect_portal", _inspect_portal)
    graph.add_node("analyze_jd", _analyze_jd)
    graph.add_node("evaluate_match", _evaluate_match)
    graph.add_node("optimize_resume", _optimize_resume)
    graph.add_node("prepare_approval", _prepare_approval)
    graph.add_node("await_human_review", _await_human_review)
    graph.add_node("finalize", _finalize)

    graph.add_conditional_edges(
        START,
        _start_route,
        {
            "discover_jobs": "discover_jobs",
            "inspect_portal": "inspect_portal",
            "analyze_jd": "analyze_jd",
            "optimize_resume": "optimize_resume"
        }
    )
    graph.add_conditional_edges(
        "discover_jobs",
        _route_after_discovery,
        {"analyze_jd": "analyze_jd", "finalize": "finalize"}
    )
    graph.add_edge("inspect_portal", "finalize")
    graph.add_conditional_edges(
        "analyze_jd",
        _route_after_analysis,
        {
            "evaluate_match": "evaluate_match",
            "prepare_approval": "prepare_approval",
            "finalize": "finalize"
        }
    )
    graph.add_conditional_edges(
        "evaluate_match",
        _route_after_match,
        {"prepare_approval": "prepare_approval", "finalize": "finalize"}
    )
    graph.add_conditional_edges(
        "optimize_resume",
        _route_after_resume_optimizer,
        {"prepare_approval": "prepare_approval", "finalize": "finalize"}
    )
    graph.add_edge("prepare_approval", "await_human_review")
    graph.add_edge("await_human_review", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile(checkpointer=checkpointer)


_workflow_graph = None
_checkpoint_connection: aiosqlite.Connection | None = None
_workflow_graph_lock = asyncio.Lock()


async def get_workflow_graph():
    """Returns the shared graph using a local SQLite checkpoint store."""
    global _workflow_graph, _checkpoint_connection
    if _workflow_graph is None:
        async with _workflow_graph_lock:
            if _workflow_graph is None:
                checkpoint_path = Path(settings.DATA_DIR) / "db" / "workflow_checkpoints.sqlite3"
                checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                _checkpoint_connection = await aiosqlite.connect(str(checkpoint_path))
                checkpointer = AsyncSqliteSaver(_checkpoint_connection)
                await checkpointer.setup()
                _workflow_graph = build_workflow_graph(checkpointer)
    return _workflow_graph


async def close_workflow_graph() -> None:
    """Closes the shared checkpoint connection during application shutdown."""
    global _workflow_graph, _checkpoint_connection
    async with _workflow_graph_lock:
        if _checkpoint_connection is not None:
            await _checkpoint_connection.close()
            _checkpoint_connection = None
            _workflow_graph = None
