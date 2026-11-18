"""Resume and Resume Version Pydantic Schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ResumeResponse(BaseModel):
    id: str
    candidate_profile_id: str
    file_name: str
    file_type: str
    raw_text: str
    parsed_json: Dict[str, Any]
    is_master: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ResumeVersionCreate(BaseModel):
    resume_id: str
    job_id: Optional[str] = None
    version_label: str = Field(..., description="e.g. 'Google - Senior Backend Engineer'")
    tailored_text: str
    tailored_json: Dict[str, Any]
    ats_score: Optional[float] = None
    grounding_verified: bool = True

class ResumeVersionResponse(BaseModel):
    id: str
    resume_id: str
    job_id: Optional[str]
    version_label: str
    tailored_text: str
    tailored_json: Dict[str, Any]
    pdf_file_path: Optional[str]
    docx_file_path: Optional[str]
    ats_score: Optional[float]
    grounding_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True

class GenerateDocumentRequest(BaseModel):
    resume_id: str
    version_id: Optional[str] = None
    custom_content: Optional[Dict[str, Any]] = None  # Optional override

class GenerateDocumentResponse(BaseModel):
    status: str
    format: str  # "PDF" or "DOCX"
    file_path: str
    file_name: str


class OptimizeResumeRequest(BaseModel):
    resume_id: str = Field(..., min_length=1, max_length=36)
    job_id: str = Field(..., min_length=1, max_length=36)
    version_label: str = Field(..., min_length=3, max_length=100)


class GroundingIssueResponse(BaseModel):
    category: str
    value: str


class GroundingReportResponse(BaseModel):
    verified: bool
    issues: List[GroundingIssueResponse] = Field(default_factory=list)
    rejected_claims: List[str] = Field(default_factory=list)


class OptimizedResumeResponse(BaseModel):
    status: str
    version_id: str
    ats_score: float
    grounding_report: GroundingReportResponse
    tailored_text: str
    tailored_json: Dict[str, Any]
    pdf_file_path: Optional[str] = None
    docx_file_path: Optional[str] = None
