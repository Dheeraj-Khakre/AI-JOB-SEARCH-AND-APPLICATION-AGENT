"""Unit Tests for Candidate and Job Profile Models & Schemas."""

import pytest
from app.schemas.candidate import (
    CandidateProfileCreate,
    ExperienceItem,
    EducationItem,
    ProjectItem
)
from app.schemas.job_profile import JobProfileCreate
from app.constants import UNIVERSAL_JOB_CATEGORIES, RemotePreference

def test_candidate_profile_schema_segregation():
    """Verify that candidate profile separates commercial experience from personal projects."""
    profile_data = CandidateProfileCreate(
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@example.com",
        phone="+1234567890",
        verified_skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        verified_experience=[
            ExperienceItem(
                company="Tech Corp",
                title="Senior Backend Engineer",
                start_date="2021-01",
                end_date="Present",
                is_current=True,
                bullet_points=["Architected distributed microservices handling 10M requests/day"],
                technologies=["Python", "FastAPI", "Redis"]
            )
        ],
        verified_education=[
            EducationItem(
                institution="State University",
                degree="B.S. Computer Science",
                field_of_study="Computer Science",
                graduation_year=2020
            )
        ],
        learning_and_projects=[
            ProjectItem(
                title="Local AI Agent",
                description="Personal open-source research project on autonomous agents",
                technologies=["LangGraph", "Ollama"],
                is_commercial=False
            )
        ]
    )

    assert profile_data.first_name == "Jane"
    assert len(profile_data.verified_experience) == 1
    assert profile_data.verified_experience[0].company == "Tech Corp"
    assert len(profile_data.learning_and_projects) == 1
    assert profile_data.learning_and_projects[0].is_commercial is False

def test_multi_job_profile_configurations():
    """Verify multiple target career profiles for a single candidate."""
    profile_backend = JobProfileCreate(
        candidate_profile_id="cand_123",
        profile_name="Python Backend Architect",
        target_job_titles=["Staff Software Engineer", "Backend Architect"],
        target_skills=["Python", "FastAPI", "SQLAlchemy", "PostgreSQL", "Docker"],
        min_years_experience=6,
        remote_preference=RemotePreference.REMOTE.value,
        is_default=True
    )

    profile_ai = JobProfileCreate(
        candidate_profile_id="cand_123",
        profile_name="AI Systems Engineer",
        target_job_titles=["AI Engineer", "LLM Systems Architect"],
        target_skills=["LangGraph", "ChromaDB", "Ollama", "PyTorch"],
        min_years_experience=4,
        remote_preference=RemotePreference.HYBRID.value,
        is_default=False
    )

    assert profile_backend.profile_name != profile_ai.profile_name
    assert profile_backend.min_years_experience == 6
    assert profile_ai.min_years_experience == 4
    assert "FastAPI" in profile_backend.target_skills
    assert "LangGraph" in profile_ai.target_skills
    assert len(UNIVERSAL_JOB_CATEGORIES) >= 25
