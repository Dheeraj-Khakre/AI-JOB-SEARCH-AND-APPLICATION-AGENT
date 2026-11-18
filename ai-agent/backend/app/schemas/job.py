"""Job Listings, JD Analysis, and Match Scoring Schemas."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class JobBase(BaseModel):
    title: str
    company_name: str
    location: Optional[str] = None
    url: str
    employment_type: Optional[str] = "FULL_TIME"
    salary_range: Optional[str] = None
    posted_date: Optional[str] = None
    status: str = "DISCOVERED"

class JobResponse(JobBase):
    id: str
    portal_id: Optional[str] = None
    external_job_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class JobSearchRequest(BaseModel):
    job_profile_id: str = Field(..., description="Target JobProfile ID to use for discovery parameters")
    limit: int = Field(20, ge=1, le=100)

class AnalyzeJDRequest(BaseModel):
    raw_description: str = Field(..., min_length=20, description="Full unformatted job posting description text")

class JDAnalysisResponse(BaseModel):
    job_id: Optional[str] = None
    mandatory_skills: List[str]
    optional_skills: List[str]
    experience_years: float
    responsibilities: List[str]
    ats_keywords: List[str]
    interview_topics: List[str]
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

class JobMatchResponse(BaseModel):
    job_id: str
    job_profile_id: str
    overall_match_score: float
    skills_match_score: float
    experience_match_score: float
    matching_skills: List[str]
    missing_skills: List[str]
    evaluated_at: datetime
