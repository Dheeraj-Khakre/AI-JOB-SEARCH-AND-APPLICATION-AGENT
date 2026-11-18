"""Candidate Profile Pydantic Schemas."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

class ExperienceItem(BaseModel):
    company: str = Field(..., description="Company or organization name")
    title: str = Field(..., description="Job role or title")
    start_date: str = Field(..., description="e.g. 2021-06")
    end_date: Optional[str] = Field(None, description="e.g. 2024-01 or Present")
    location: Optional[str] = None
    is_current: bool = False
    bullet_points: List[str] = Field(default_factory=list, description="Accomplishments and responsibilities")
    technologies: List[str] = Field(default_factory=list)

class EducationItem(BaseModel):
    institution: str = Field(..., description="University or College")
    degree: str = Field(..., description="e.g. Bachelor of Technology, Master of Science")
    field_of_study: str = Field(..., description="e.g. Computer Science")
    graduation_year: Optional[int] = None
    gpa: Optional[str] = None

class ProjectItem(BaseModel):
    title: str = Field(..., description="Project name")
    description: str = Field(..., description="Project overview and impact")
    url: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    is_commercial: bool = False  # Separates commercial from personal learning

class CandidateProfileBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    location_city: Optional[str] = None
    location_country: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None

class CandidateProfileCreate(CandidateProfileBase):
    user_id: Optional[str] = None
    verified_skills: List[str] = Field(default_factory=list)
    verified_experience: List[ExperienceItem] = Field(default_factory=list)
    verified_education: List[EducationItem] = Field(default_factory=list)
    learning_and_projects: List[ProjectItem] = Field(default_factory=list)

class CandidateProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    location_city: Optional[str] = None
    location_country: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    verified_skills: Optional[List[str]] = None
    verified_experience: Optional[List[ExperienceItem]] = None
    verified_education: Optional[List[EducationItem]] = None
    learning_and_projects: Optional[List[ProjectItem]] = None

class CandidateProfileResponse(CandidateProfileBase):
    id: str
    user_id: str
    verified_skills: List[str]
    verified_experience: List[Dict[str, Any]]
    verified_education: List[Dict[str, Any]]
    learning_and_projects: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
