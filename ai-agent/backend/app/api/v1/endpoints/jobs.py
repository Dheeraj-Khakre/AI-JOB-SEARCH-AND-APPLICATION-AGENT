"""Job Discovery, JD Analysis, and Match Scoring API Endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.discovery_agent import JobDiscoveryAgent
from app.agents.jd_analysis_agent import JDAnalysisAgent, ParsedJDRequirements
from app.connectors.registry import PortalConnectorRegistry
from app.core.exceptions import PortalConnectorError
from app.db.models.candidate import CandidateProfile
from app.db.models.job import Job, JobDescription, JobMatch
from app.db.models.job_profile import JobProfile
from app.db.session import get_db
from app.schemas.job import (
    AnalyzeJDRequest,
    JDAnalysisResponse,
    JobMatchResponse,
    JobResponse,
    JobSearchRequest,
)

router = APIRouter(prefix="/jobs", tags=["Job Discovery & JD Analysis"])


async def _extract_job_description(job: Job) -> str:
    try:
        connector = await PortalConnectorRegistry.resolve_for_url(job.url)
        raw_text = await connector.extract_job_description(job.url)
    except PortalConnectorError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc
    if not raw_text or not raw_text.strip():
        raise HTTPException(
            status_code=422,
            detail="No job description was available to analyze. Provide the posting text."
        )
    return raw_text


@router.post("/discover", response_model=List[JobResponse])
async def trigger_job_discovery(
    request: JobSearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Agent 1: Executes concurrent multi-portal job search using candidate's JobProfile.
    Deduplicates listings and persists new jobs into the database.
    """
    profile = await db.get(JobProfile, request.job_profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job Profile '{request.job_profile_id}' not found."
        )

    try:
        discovered = await JobDiscoveryAgent.discover_jobs(
            job_profile=profile,
            db=db,
            limit_per_portal=request.limit
        )
    except PortalConnectorError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc
    return discovered

@router.get("/", response_model=List[JobResponse])
async def list_jobs(
    status_filter: Optional[str] = Query(None, alias="status"),
    search_query: Optional[str] = Query(None, alias="q"),
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Lists discovered jobs with optional status and title search filters."""
    stmt = select(Job).order_by(Job.created_at.desc())
    if status_filter:
        stmt = stmt.where(Job.status == status_filter.upper())
    if search_query:
        title_match = Job.title.ilike(f"%{search_query}%")
        company_match = Job.company_name.ilike(f"%{search_query}%")
        stmt = stmt.where(title_match | company_match)
    stmt = stmt.offset(skip).limit(limit)

    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/{job_id}", response_model=JobResponse)
async def get_job_by_id(job_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves specific job listing details."""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job listing not found.")
    return job

@router.post("/analyze-text", response_model=JDAnalysisResponse)
async def analyze_raw_jd_text(request: AnalyzeJDRequest):
    """Agent 3: Ad-hoc semantic analysis of raw JD text without existing job record."""
    parsed = await JDAnalysisAgent.analyze_jd_text(request.raw_description)
    return JDAnalysisResponse(
        mandatory_skills=parsed.mandatory_skills,
        optional_skills=parsed.optional_skills,
        experience_years=parsed.experience_years,
        responsibilities=parsed.responsibilities,
        ats_keywords=parsed.ats_keywords,
        interview_topics=parsed.interview_topics
    )

@router.post("/{job_id}/analyze", response_model=JDAnalysisResponse)
async def analyze_stored_job_description(
    job_id: str,
    request: Optional[AnalyzeJDRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    """Agent 3: Analyzes a stored job's JD and persists extraction into 'job_descriptions'."""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job listing not found.")

    existing_desc = await db.execute(select(JobDescription).where(JobDescription.job_id == job_id))
    desc_record = existing_desc.scalar_one_or_none()
    if request:
        raw_text = request.raw_description
    elif desc_record and desc_record.raw_description.strip():
        raw_text = desc_record.raw_description
    else:
        raw_text = await _extract_job_description(job)

    parsed = await JDAnalysisAgent.analyze_jd_text(raw_text)

    if desc_record:
        desc_record.raw_description = raw_text
        desc_record.extracted_mandatory_skills = parsed.mandatory_skills
        desc_record.extracted_optional_skills = parsed.optional_skills
        desc_record.extracted_experience_years = parsed.experience_years
        desc_record.extracted_responsibilities = parsed.responsibilities
        desc_record.extracted_ats_keywords = parsed.ats_keywords
        desc_record.extracted_interview_topics = parsed.interview_topics
    else:
        desc_record = JobDescription(
            job_id=job_id,
            raw_description=raw_text,
            extracted_mandatory_skills=parsed.mandatory_skills,
            extracted_optional_skills=parsed.optional_skills,
            extracted_experience_years=parsed.experience_years,
            extracted_responsibilities=parsed.responsibilities,
            extracted_ats_keywords=parsed.ats_keywords,
            extracted_interview_topics=parsed.interview_topics
        )
        db.add(desc_record)

    job.status = "PROCESSED"
    await db.commit()
    await db.refresh(desc_record)

    return JDAnalysisResponse(
        job_id=job_id,
        mandatory_skills=desc_record.extracted_mandatory_skills,
        optional_skills=desc_record.extracted_optional_skills,
        experience_years=float(desc_record.extracted_experience_years or 0.0),
        responsibilities=desc_record.extracted_responsibilities,
        ats_keywords=desc_record.extracted_ats_keywords,
        interview_topics=desc_record.extracted_interview_topics,
        analyzed_at=desc_record.analyzed_at
    )

@router.post("/{job_id}/match/{profile_id}", response_model=JobMatchResponse)
async def evaluate_candidate_match(
    job_id: str,
    profile_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Calculates compatibility match score between a candidate JobProfile and a Job."""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    job_profile = await db.get(JobProfile, profile_id)
    if not job_profile:
        raise HTTPException(status_code=404, detail="Job Profile not found.")

    candidate = await db.get(CandidateProfile, job_profile.candidate_profile_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate Master Profile not found.")

    # Retrieve or perform analysis
    desc_result = await db.execute(select(JobDescription).where(JobDescription.job_id == job_id))
    desc = desc_result.scalar_one_or_none()

    if not desc:
        raw_text = await _extract_job_description(job)
        parsed = await JDAnalysisAgent.analyze_jd_text(raw_text)
        desc = JobDescription(
            job_id=job_id,
            raw_description=raw_text,
            extracted_mandatory_skills=parsed.mandatory_skills,
            extracted_optional_skills=parsed.optional_skills,
            extracted_experience_years=parsed.experience_years,
            extracted_responsibilities=parsed.responsibilities,
            extracted_ats_keywords=parsed.ats_keywords,
            extracted_interview_topics=parsed.interview_topics
        )
        job.status = "PROCESSED"
        db.add(desc)
    else:
        parsed = ParsedJDRequirements(
            mandatory_skills=desc.extracted_mandatory_skills,
            optional_skills=desc.extracted_optional_skills,
            experience_years=float(desc.extracted_experience_years or 0.0),
            responsibilities=desc.extracted_responsibilities,
            ats_keywords=desc.extracted_ats_keywords,
            interview_topics=desc.extracted_interview_topics
        )

    # Target-profile preferences are not evidence of candidate qualifications.
    evaluation = JDAnalysisAgent.calculate_compatibility(
        candidate_skills=candidate.verified_skills,
        candidate_exp_years=JDAnalysisAgent.calculate_verified_experience_years(
            candidate.verified_experience
        ),
        jd_requirements=parsed
    )

    # Persist or update match record
    match_result = await db.execute(
        select(JobMatch).where(
            JobMatch.job_id == job_id,
            JobMatch.job_profile_id == profile_id
        )
    )
    match_record = match_result.scalar_one_or_none()

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

    return JobMatchResponse(
        job_id=job_id,
        job_profile_id=profile_id,
        overall_match_score=float(match_record.overall_match_score),
        skills_match_score=float(match_record.skills_match_score),
        experience_match_score=float(match_record.experience_match_score),
        matching_skills=match_record.matching_skills,
        missing_skills=match_record.missing_skills,
        evaluated_at=match_record.evaluated_at
    )
