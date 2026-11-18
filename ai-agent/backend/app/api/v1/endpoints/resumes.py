"""Resume Upload, Parsing, Versioning, and Document Rendering Endpoints."""

import os
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.resume_optimizer_agent import ResumeOptimizerAgent
from app.config import settings
from app.db.models.candidate import CandidateProfile
from app.db.models.job import Job, JobDescription
from app.db.models.resume import Resume, ResumeVersion
from app.db.session import get_db
from app.documents.docx_generator import ATSDocxGenerator
from app.documents.parser import UnifiedResumeParser
from app.documents.pdf_generator import ATSPdfGenerator
from app.schemas.resume import (
    GenerateDocumentResponse,
    OptimizedResumeResponse,
    OptimizeResumeRequest,
    ResumeResponse,
    ResumeVersionCreate,
    ResumeVersionResponse,
)

router = APIRouter(prefix="/resumes", tags=["Resumes & Document Generation"])

@router.post("/upload", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
async def upload_and_parse_resume(
    candidate_profile_id: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Uploads and parses a resume, then saves it as the candidate master record."""
    # Verify candidate exists
    candidate = await db.get(CandidateProfile, candidate_profile_id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate profile '{candidate_profile_id}' not found."
        )

    if file.content_type not in {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF and DOCX resume uploads are supported.",
        )

    content = await file.read(settings.MAX_RESUME_UPLOAD_BYTES + 1)
    if len(content) > settings.MAX_RESUME_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Resume exceeds the {settings.MAX_RESUME_UPLOAD_BYTES // (1024 * 1024)} MB limit."
            ),
        )
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty."
        )

    filename = (file.filename or "").lower()
    if not filename.endswith(".pdf") and not filename.endswith(".docx"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Resume filename must end with .pdf or .docx.",
        )

    parsed_result = UnifiedResumeParser.parse_document(content, file.filename)

    resume = Resume(
        candidate_profile_id=candidate_profile_id,
        file_name=file.filename,
        file_type=parsed_result["file_type"],
        raw_text=parsed_result["raw_text"],
        parsed_json=parsed_result["parsed_json"],
        is_master=True
    )
    db.add(resume)
    await db.flush()
    suffix = ".pdf" if parsed_result["file_type"] == "PDF" else ".docx"
    original_path = (
        Path(settings.RESUME_STORAGE_DIR)
        / f"{resume.id}_original{suffix}"
    )
    original_path.parent.mkdir(parents=True, exist_ok=True)
    original_path.write_bytes(content)
    await db.commit()
    await db.refresh(resume)

    # Pre-render initial ATS PDF and DOCX in data/resumes
    try:
        render_payload = resume.parsed_json.copy()
        render_payload["full_name"] = f"{candidate.first_name} {candidate.last_name}"
        if not render_payload.get("contact_info"):
            render_payload["contact_info"] = {
                "name": f"{candidate.first_name} {candidate.last_name}",
                "email": candidate.email,
                "phone": candidate.phone,
                "linkedin_url": candidate.linkedin_url,
                "github_url": candidate.github_url
            }

        pdf_path = f"{settings.RESUME_STORAGE_DIR}/{resume.id}_master.pdf"
        docx_path = f"{settings.RESUME_STORAGE_DIR}/{resume.id}_master.docx"

        ATSPdfGenerator.generate_pdf(render_payload, pdf_path)
        ATSDocxGenerator.generate_docx(render_payload, docx_path)
    except Exception:
        # Non-fatal during upload
        pass

    return resume

@router.get("/candidate/{candidate_id}", response_model=List[ResumeResponse])
async def list_candidate_resumes(candidate_id: str, db: AsyncSession = Depends(get_db)):
    """Lists all resumes for a candidate."""
    result = await db.execute(
        select(Resume)
        .where(Resume.candidate_profile_id == candidate_id)
        .order_by(Resume.created_at.desc())
    )
    return result.scalars().all()

@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(resume_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves structured parsed resume data."""
    resume = await db.get(Resume, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return resume

@router.post("/{resume_id}/generate-pdf", response_model=GenerateDocumentResponse)
async def render_pdf_resume(resume_id: str, db: AsyncSession = Depends(get_db)):
    """Renders the ATS-compliant PDF document for the given resume."""
    resume = await db.get(Resume, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    output_path = f"{settings.RESUME_STORAGE_DIR}/{resume.id}.pdf"
    rendered_file = ATSPdfGenerator.generate_pdf(resume.parsed_json, output_path)

    return GenerateDocumentResponse(
        status="GENERATED",
        format="PDF",
        file_path=rendered_file,
        file_name=Path(rendered_file).name
    )

@router.post("/{resume_id}/generate-docx", response_model=GenerateDocumentResponse)
async def render_docx_resume(resume_id: str, db: AsyncSession = Depends(get_db)):
    """Renders the ATS-compliant DOCX document for the given resume."""
    resume = await db.get(Resume, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    output_path = f"{settings.RESUME_STORAGE_DIR}/{resume.id}.docx"
    rendered_file = ATSDocxGenerator.generate_docx(resume.parsed_json, output_path)

    return GenerateDocumentResponse(
        status="GENERATED",
        format="DOCX",
        file_path=rendered_file,
        file_name=Path(rendered_file).name
    )

@router.get("/{resume_id}/download/{doc_format}")
async def download_resume_document(
    resume_id: str,
    doc_format: str,
    db: AsyncSession = Depends(get_db)
):
    """Downloads the generated PDF or DOCX binary."""
    fmt = doc_format.lower()
    if fmt not in ["pdf", "docx"]:
        raise HTTPException(status_code=400, detail="Format must be 'pdf' or 'docx'.")

    file_path = Path(f"{settings.RESUME_STORAGE_DIR}/{resume_id}.{fmt}")
    if not file_path.exists():
        # Check master variant
        file_path = Path(f"{settings.RESUME_STORAGE_DIR}/{resume_id}_master.{fmt}")
    if not file_path.exists():
        # Trigger on-demand generation
        resume = await db.get(Resume, resume_id)
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found.")
        target = f"{settings.RESUME_STORAGE_DIR}/{resume_id}.{fmt}"
        if fmt == "pdf":
            ATSPdfGenerator.generate_pdf(resume.parsed_json, target)
        else:
            ATSDocxGenerator.generate_docx(resume.parsed_json, target)
        file_path = Path(target)

    media_type = (
        "application/pdf"
        if fmt == "pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    return FileResponse(path=str(file_path), media_type=media_type, filename=file_path.name)

# Resume Optimization & Versioning Endpoints
@router.post("/optimize", response_model=OptimizedResumeResponse)
async def optimize_resume(
    request: OptimizeResumeRequest,
    db: AsyncSession = Depends(get_db)
):
    """Creates a grounded, ATS-tailored resume version for a stored JD."""
    resume = await db.get(Resume, request.resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Base resume not found.")

    candidate = await db.get(CandidateProfile, resume.candidate_profile_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate profile not found.")

    job = await db.get(Job, request.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job listing not found.")

    description_result = await db.execute(
        select(JobDescription).where(JobDescription.job_id == request.job_id)
    )
    description = description_result.scalar_one_or_none()
    if not description:
        raise HTTPException(
            status_code=422,
            detail="The job description must be analyzed before resume optimization."
        )

    result = ResumeOptimizerAgent.optimize(
        candidate_profile=candidate,
        resume=resume,
        job=job,
        description=description
    )

    version = ResumeVersion(
        resume_id=request.resume_id,
        job_id=request.job_id,
        version_label=request.version_label,
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
    return OptimizedResumeResponse(
        status="OPTIMIZED",
        version_id=version.id,
        ats_score=result.ats_score,
        grounding_report={
            "verified": result.grounding_report.verified,
            "issues": [
                issue.model_dump() for issue in result.grounding_report.issues
            ],
            "rejected_claims": result.grounding_report.rejected_claims
        },
        tailored_text=result.tailored_text,
        tailored_json=result.tailored_json,
        pdf_file_path=version.pdf_file_path,
        docx_file_path=version.docx_file_path
    )


@router.post(
    "/versions/",
    response_model=ResumeVersionResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_resume_version(
    version_in: ResumeVersionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Creates a customized resume version tailored for a specific JD."""
    resume = await db.get(Resume, version_in.resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Base resume not found.")
    candidate = await db.get(CandidateProfile, resume.candidate_profile_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate profile not found.")

    ground_facts = ResumeOptimizerAgent.collect_ground_facts(candidate, resume)
    grounding_report = ResumeOptimizerAgent.verify_grounding(
        version_in.tailored_json,
        ground_facts
    )
    if not grounding_report.verified:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Resume version contains unsupported claims.",
                "issues": [issue.model_dump() for issue in grounding_report.issues],
                "rejected_claims": grounding_report.rejected_claims
            }
        )

    version = ResumeVersion(
        resume_id=version_in.resume_id,
        job_id=version_in.job_id,
        version_label=version_in.version_label,
        tailored_text=version_in.tailored_text,
        tailored_json=version_in.tailored_json,
        ats_score=version_in.ats_score,
        grounding_verified=True
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)

    # Automatically generate tailored PDF and DOCX files for this version
    try:
        pdf_path = f"{settings.RESUME_STORAGE_DIR}/ver_{version.id}.pdf"
        docx_path = f"{settings.RESUME_STORAGE_DIR}/ver_{version.id}.docx"
        ATSPdfGenerator.generate_pdf(version.tailored_json, pdf_path)
        ATSDocxGenerator.generate_docx(version.tailored_json, docx_path)
        version.pdf_file_path = pdf_path
        version.docx_file_path = docx_path
        await db.commit()
        await db.refresh(version)
    except Exception:
        pass

    return version

@router.get("/{resume_id}/versions", response_model=List[ResumeVersionResponse])
async def list_resume_versions(resume_id: str, db: AsyncSession = Depends(get_db)):
    """Lists all versions created for a resume."""
    result = await db.execute(
        select(ResumeVersion)
        .where(ResumeVersion.resume_id == resume_id)
        .order_by(ResumeVersion.created_at.desc())
    )
    return result.scalars().all()

@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(resume_id: str, db: AsyncSession = Depends(get_db)):
    """Deletes a resume, its versions, and associated rendered files."""
    resume = await db.get(Resume, resume_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    # Cleanup local files
    for ext in ["pdf", "docx"]:
        for prefix in [
            f"{resume_id}",
            f"{resume_id}_master",
            f"{resume_id}_original",
        ]:
            p = Path(f"{settings.RESUME_STORAGE_DIR}/{prefix}.{ext}")
            if p.exists():
                try:
                    os.remove(p)
                except OSError:
                    pass

    version_result = await db.execute(
        select(ResumeVersion).where(ResumeVersion.resume_id == resume_id)
    )
    for version in version_result.scalars().all():
        for file_path in (version.pdf_file_path, version.docx_file_path):
            if file_path:
                rendered = Path(file_path)
                if rendered.exists():
                    try:
                        rendered.unlink()
                    except OSError:
                        pass

    await db.delete(resume)
    await db.commit()
    return None
