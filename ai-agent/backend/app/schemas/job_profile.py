"""Job Profile Pydantic Schemas."""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from app.constants import RemotePreference, EmploymentType

class JobProfileBase(BaseModel):
    profile_name: str = Field(..., description="e.g. Senior Python Backend Architect")
    target_job_titles: List[str] = Field(..., description="e.g. ['AI Engineer', 'Backend Lead']")
    target_skills: List[str] = Field(..., description="e.g. ['FastAPI', 'Docker', 'PostgreSQL']")
    min_years_experience: int = Field(0, ge=0)
    preferred_industries: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    remote_preference: str = Field(default=RemotePreference.ANY.value)
    expected_salary_min: Optional[float] = None
    expected_salary_currency: str = Field(default="USD")
    employment_type: str = Field(default=EmploymentType.FULL_TIME.value)
    education_requirements: List[str] = Field(default_factory=list)
    is_default: bool = False

class JobProfileCreate(JobProfileBase):
    candidate_profile_id: Optional[str] = None

class JobProfileUpdate(BaseModel):
    profile_name: Optional[str] = None
    target_job_titles: Optional[List[str]] = None
    target_skills: Optional[List[str]] = None
    min_years_experience: Optional[int] = Field(None, ge=0)
    preferred_industries: Optional[List[str]] = None
    preferred_locations: Optional[List[str]] = None
    remote_preference: Optional[str] = None
    expected_salary_min: Optional[float] = None
    expected_salary_currency: Optional[str] = None
    employment_type: Optional[str] = None
    education_requirements: Optional[List[str]] = None
    is_default: Optional[bool] = None

class JobProfileResponse(JobProfileBase):
    id: str
    candidate_profile_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
