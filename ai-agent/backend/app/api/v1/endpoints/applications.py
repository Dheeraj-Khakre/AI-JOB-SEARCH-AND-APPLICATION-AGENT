"""Phase 9 browser application preparation and HITL submission boundary."""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.automation.application_assistant import ApplicationAssistant
from app.automation.approval_gate import ApplicationApprovalGate
from app.config import settings
from app.core.exceptions import (
    AntiBotChallengeDetectedError,
    InvalidApprovalTokenError,
    PortalConnectorError,
)
from app.db.models.candidate import CandidateProfile
from app.db.models.job import Job
from app.db.models.resume import Resume, ResumeVersion
from app.db.session import get_db
from app.schemas.application import (
    ApplicationApproveRequest,
    ApplicationPrepareRequest,
    ApplicationPrepareResponse,
    ApplicationSubmitRequest,
)

router = APIRouter(prefix="/applications", tags=["Application Assistant"])
approval_gate = ApplicationApprovalGate()
application_assistant = ApplicationAssistant()


@router.post("/prepare", response_model=ApplicationPrepareResponse)
async def prepare_application(
    request: ApplicationPrepareRequest,
    db: AsyncSession = Depends(get_db),
):
    if not request.target_url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid HTTP or HTTPS target URL is required.",
        )

    job = await db.get(Job, request.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job listing not found.")
    resume_version = await db.get(ResumeVersion, request.resume_version_id)
    if not resume_version:
        raise HTTPException(status_code=404, detail="Resume version not found.")
    if resume_version.job_id and resume_version.job_id != job.id:
        raise HTTPException(
            status_code=422,
            detail="Resume version is not tailored for the selected job.",
        )
    if not resume_version.grounding_verified:
        raise HTTPException(
            status_code=422,
            detail="Resume version must pass grounding verification.",
        )

    resume_result = await db.execute(
        select(Resume).where(Resume.id == resume_version.resume_id)
    )
    resume = resume_result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Base resume not found.")
    candidate = await db.get(CandidateProfile, resume.candidate_profile_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate profile not found.")

    preview = ApplicationAssistant.build_preview(
        candidate_profile=candidate,
        resume_version=resume_version,
        job=job,
        target_url=request.target_url,
    )
    missing = application_assistant.validate_preview(preview)
    approval_id = str(uuid4())
    approval_gate.create_pending(approval_id, preview)
    return ApplicationPrepareResponse(
        approval_id=approval_id,
        status="AWAITING_APPROVAL",
        expires_in_seconds=settings.APPROVAL_TOKEN_EXPIRY_SECONDS,
        preview=preview,
        missing_fields=missing,
    )


@router.post("/{approval_id}/approve", response_model=ApplicationPrepareResponse)
async def approve_application(
    approval_id: str,
    request: ApplicationApproveRequest,
):
    try:
        token = approval_gate.approve(approval_id, request.preview)
    except InvalidApprovalTokenError as exc:
        raise HTTPException(status_code=409, detail=exc.message) from exc
    return ApplicationPrepareResponse(
        approval_id=approval_id,
        status="APPROVED",
        expires_in_seconds=settings.APPROVAL_TOKEN_EXPIRY_SECONDS,
        preview=request.preview,
        missing_fields=application_assistant.validate_preview(request.preview),
        approval_token=token,
    )


@router.post("/{approval_id}/submit")
async def submit_application(
    approval_id: str,
    request: ApplicationSubmitRequest,
):
    if application_assistant.validate_preview(request.preview):
        raise HTTPException(
            status_code=422,
            detail="Application preview is incomplete.",
        )
    try:
        await application_assistant.submit(
            target_url=request.preview["target_url"],
            preview=request.preview,
            approval_id=approval_id,
            approval_token=request.approval_token,
            approval_gate=approval_gate,
        )
    except InvalidApprovalTokenError as exc:
        raise HTTPException(status_code=409, detail=exc.message) from exc
    except AntiBotChallengeDetectedError as exc:
        raise HTTPException(status_code=423, detail=exc.message) from exc
    except PortalConnectorError as exc:
        raise HTTPException(status_code=409, detail=exc.message) from exc
