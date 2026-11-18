"""Tests for the checkpointed LangGraph job-search workflow."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.agents import job_search_orchestrator
from app.agents.jd_analysis_agent import ParsedJDRequirements
from app.agents.job_search_orchestrator import (
    MAX_WORKFLOW_ITERATIONS,
    WorkflowStateError,
    _advance,
    build_workflow_graph,
    close_workflow_graph,
    get_workflow_graph,
)


def _config(session_id: str, db_session=None):
    configurable = {"thread_id": session_id}
    if db_session is not None:
        configurable["db_session"] = db_session
    return {"configurable": configurable}


@pytest.mark.asyncio
async def test_analyze_workflow_records_agent_transitions():
    graph = build_workflow_graph(MemorySaver())
    session_id = str(uuid4())

    with patch(
        "app.agents.job_search_orchestrator.JDAnalysisAgent.analyze_jd_text",
        new=AsyncMock(return_value=ParsedJDRequirements(
            mandatory_skills=["Python"],
            experience_years=4
        ))
    ):
        result = await graph.ainvoke(
            {
                "session_id": session_id,
                "mode": "analyze",
                "raw_jd_text": "Python engineer role requiring four years of experience."
            },
            _config(session_id)
        )

    assert result["workflow_status"] == "COMPLETED"
    assert result["agent_history"] == ["jd_analysis", "workflow_complete"]
    assert result["iteration_count"] == 2
    assert result["analyzed_jd"]["mandatory_skills"] == ["Python"]


@pytest.mark.asyncio
async def test_review_interrupt_persists_and_resumes_with_approval_decision():
    graph = build_workflow_graph(MemorySaver())
    session_id = str(uuid4())
    config = _config(session_id)

    with patch(
        "app.agents.job_search_orchestrator.JDAnalysisAgent.analyze_jd_text",
        new=AsyncMock(return_value=ParsedJDRequirements(mandatory_skills=["Python"]))
    ):
        await graph.ainvoke(
            {
                "session_id": session_id,
                "mode": "analyze",
                "raw_jd_text": "A software engineering role requiring Python expertise.",
                "require_human_approval": True
            },
            config
        )

    paused = await graph.aget_state(config)
    assert paused.values["approval_status"] == "AWAITING_REVIEW"
    assert paused.values["workflow_status"] == "AWAITING_REVIEW"
    assert paused.tasks[0].interrupts[0].value["type"] == "human_review_required"

    await graph.ainvoke(Command(resume={"decision": "approve"}), config)
    completed = await graph.aget_state(config)
    assert completed.values["approval_status"] == "APPROVED"
    assert completed.values["workflow_status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_review_rejection_ends_workflow_without_approval():
    graph = build_workflow_graph(MemorySaver())
    session_id = str(uuid4())
    config = _config(session_id)

    with patch(
        "app.agents.job_search_orchestrator.JDAnalysisAgent.analyze_jd_text",
        new=AsyncMock(return_value=ParsedJDRequirements())
    ):
        await graph.ainvoke(
            {
                "session_id": session_id,
                "mode": "analyze",
                "raw_jd_text": "A general role description that is long enough to analyze.",
                "require_human_approval": True
            },
            config
        )

    await graph.ainvoke(Command(resume={"decision": "reject"}), config)
    completed = await graph.aget_state(config)
    assert completed.values["approval_status"] == "REJECTED"
    assert completed.values["workflow_status"] == "REJECTED"


@pytest.mark.asyncio
async def test_discovery_branch_uses_job_profile_and_records_transitions():
    graph = build_workflow_graph(MemorySaver())
    session_id = str(uuid4())
    profile = SimpleNamespace(id="profile-1")
    db = SimpleNamespace(get=AsyncMock(return_value=profile))

    with patch(
        "app.agents.job_search_orchestrator.JobDiscoveryAgent.discover_jobs",
        new=AsyncMock(return_value=[])
    ) as discover:
        result = await graph.ainvoke(
            {
                "session_id": session_id,
                "mode": "discover",
                "active_job_profile_id": "profile-1"
            },
            _config(session_id, db)
        )

    discover.assert_awaited_once_with(profile, db)
    assert result["discovered_jobs"] == []
    assert result["workflow_status"] == "COMPLETED"
    assert result["agent_history"] == ["job_discovery", "workflow_complete"]


@pytest.mark.asyncio
async def test_analyze_and_match_branch_uses_verified_candidate_skills():
    graph = build_workflow_graph(MemorySaver())
    session_id = str(uuid4())
    job = SimpleNamespace(
        id="job-1",
        title="Python Engineer",
        company_name="Example",
        url="https://jobs.example/1",
        status="DISCOVERED"
    )
    profile = SimpleNamespace(
        id="profile-1",
        candidate_profile_id="candidate-1",
        target_skills=["Python"]
    )
    candidate = SimpleNamespace(
        verified_skills=[],
        verified_experience=[]
    )
    no_record = SimpleNamespace(scalar_one_or_none=lambda: None)
    db = SimpleNamespace(
        get=AsyncMock(side_effect=[job, profile, candidate]),
        execute=AsyncMock(return_value=no_record),
        add=Mock(),
        commit=AsyncMock(),
        refresh=AsyncMock()
    )

    with patch(
        "app.agents.job_search_orchestrator.JDAnalysisAgent.analyze_jd_text",
        new=AsyncMock(return_value=ParsedJDRequirements(
            mandatory_skills=["Python"],
            experience_years=4
        ))
    ):
        result = await graph.ainvoke(
            {
                "session_id": session_id,
                "mode": "analyze",
                "active_job_profile_id": "profile-1",
                "selected_job_id": "job-1",
                "raw_jd_text": "Python Engineer role requiring four years of experience."
            },
            _config(session_id, db)
        )

    assert result["match_result"]["missing_skills"] == ["Python"]
    assert result["match_result"]["matching_skills"] == []
    assert result["compatibility_score"] == 0.0
    assert result["agent_history"] == [
        "jd_analysis",
        "compatibility_evaluation",
        "workflow_complete"
    ]


@pytest.mark.asyncio
async def test_portal_inspection_branch_records_report():
    graph = build_workflow_graph(MemorySaver())
    session_id = str(uuid4())
    report = SimpleNamespace(to_dict=lambda: {"portal_name": "Example ATS"})

    with patch(
        "app.agents.job_search_orchestrator.PortalDiscoveryAgent.inspect_url",
        new=AsyncMock(return_value=report)
    ):
        result = await graph.ainvoke(
            {
                "session_id": session_id,
                "mode": "inspect",
                "target_url": "https://jobs.example/careers"
            },
            _config(session_id)
        )

    assert result["current_portal_report"] == {"portal_name": "Example ATS"}
    assert result["workflow_status"] == "COMPLETED"
    assert result["agent_history"] == ["portal_discovery", "workflow_complete"]


def test_workflow_iteration_budget_is_enforced():
    with pytest.raises(WorkflowStateError, match="maximum"):
        _advance({"iteration_count": MAX_WORKFLOW_ITERATIONS}, "another_agent")


@pytest.mark.asyncio
async def test_sqlite_checkpoint_can_be_loaded_by_a_new_graph(tmp_path):
    session_id = str(uuid4())
    config = _config(session_id)
    checkpoint_path = tmp_path / "db" / "workflow_checkpoints.sqlite3"
    with patch.object(job_search_orchestrator.settings, "DATA_DIR", str(tmp_path)):
        graph = await get_workflow_graph()
        try:
            with patch(
                "app.agents.job_search_orchestrator.JDAnalysisAgent.analyze_jd_text",
                new=AsyncMock(return_value=ParsedJDRequirements(mandatory_skills=["Python"]))
            ):
                await graph.ainvoke(
                    {
                        "session_id": session_id,
                        "mode": "analyze",
                        "raw_jd_text": "A software engineering role requiring Python expertise.",
                        "require_human_approval": True
                    },
                    config
                )
            await close_workflow_graph()

            restored_graph = await get_workflow_graph()
            snapshot = await restored_graph.aget_state(config)
            assert snapshot.values["approval_status"] == "AWAITING_REVIEW"
            assert snapshot.values["session_id"] == session_id
        finally:
            await close_workflow_graph()

    assert checkpoint_path.exists()
