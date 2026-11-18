"""Target Career Profiles API Endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.db.session import get_db
from app.db.models.job_profile import JobProfile
from app.db.models.candidate import CandidateProfile
from app.schemas.job_profile import (
    JobProfileCreate,
    JobProfileUpdate,
    JobProfileResponse
)
from app.constants import UNIVERSAL_JOB_CATEGORIES

router = APIRouter(prefix="/job-profiles", tags=["Target Career Profiles"])

@router.get("/categories/list", response_model=List[str])
async def list_universal_job_categories():
    """Returns the list of 25+ universal job role categories supported out of the box."""
    return UNIVERSAL_JOB_CATEGORIES

@router.post("/", response_model=JobProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_job_profile(
    profile_in: JobProfileCreate,
    db: AsyncSession = Depends(get_db)
):
    """Creates a targeted career profile for a candidate."""
    # Ensure candidate profile exists
    candidate = await db.get(CandidateProfile, profile_in.candidate_profile_id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate profile with ID '{profile_in.candidate_profile_id}' not found."
        )

    # If this is marked as default, unset other defaults for this candidate
    if profile_in.is_default:
        await db.execute(
            update(JobProfile)
            .where(JobProfile.candidate_profile_id == profile_in.candidate_profile_id)
            .values(is_default=False)
        )

    job_profile = JobProfile(
        candidate_profile_id=profile_in.candidate_profile_id,
        profile_name=profile_in.profile_name,
        target_job_titles=profile_in.target_job_titles,
        target_skills=profile_in.target_skills,
        min_years_experience=profile_in.min_years_experience,
        preferred_industries=profile_in.preferred_industries,
        preferred_locations=profile_in.preferred_locations,
        remote_preference=profile_in.remote_preference,
        expected_salary_min=profile_in.expected_salary_min,
        expected_salary_currency=profile_in.expected_salary_currency,
        employment_type=profile_in.employment_type,
        education_requirements=profile_in.education_requirements,
        is_default=profile_in.is_default
    )
    db.add(job_profile)
    await db.commit()
    await db.refresh(job_profile)
    return job_profile

@router.get("/candidate/{candidate_id}", response_model=List[JobProfileResponse])
async def list_job_profiles_for_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Lists all targeted career profiles configured for a specific candidate."""
    result = await db.execute(
        select(JobProfile)
        .where(JobProfile.candidate_profile_id == candidate_id)
        .order_by(JobProfile.is_default.desc(), JobProfile.created_at.desc())
    )
    return result.scalars().all()

@router.get("/{profile_id}", response_model=JobProfileResponse)
async def get_job_profile(profile_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves a specific target career profile."""
    job_profile = await db.get(JobProfile, profile_id)
    if not job_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job profile with ID '{profile_id}' not found."
        )
    return job_profile

@router.put("/{profile_id}", response_model=JobProfileResponse)
async def update_job_profile(
    profile_id: str,
    update_in: JobProfileUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Updates a targeted career profile."""
    job_profile = await db.get(JobProfile, profile_id)
    if not job_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job profile with ID '{profile_id}' not found."
        )

    update_data = update_in.model_dump(exclude_unset=True)

    if update_data.get("is_default") is True:
        await db.execute(
            update(JobProfile)
            .where(JobProfile.candidate_profile_id == job_profile.candidate_profile_id)
            .values(is_default=False)
        )

    for key, val in update_data.items():
        setattr(job_profile, key, val)

    await db.commit()
    await db.refresh(job_profile)
    return job_profile

@router.post("/{profile_id}/set-default", response_model=JobProfileResponse)
async def set_default_job_profile(profile_id: str, db: AsyncSession = Depends(get_db)):
    """Sets a job profile as the primary active default for job searches."""
    job_profile = await db.get(JobProfile, profile_id)
    if not job_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job profile with ID '{profile_id}' not found."
        )

    await db.execute(
        update(JobProfile)
        .where(JobProfile.candidate_profile_id == job_profile.candidate_profile_id)
        .values(is_default=False)
    )

    job_profile.is_default = True
    await db.commit()
    await db.refresh(job_profile)
    return job_profile

@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job_profile(profile_id: str, db: AsyncSession = Depends(get_db)):
    """Deletes a targeted career profile."""
    job_profile = await db.get(JobProfile, profile_id)
    if not job_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job profile with ID '{profile_id}' not found."
        )
    await db.delete(job_profile)
    await db.commit()
    return None
