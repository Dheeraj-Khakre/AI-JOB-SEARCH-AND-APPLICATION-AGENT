"""Candidate Profile API Endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models.candidate import CandidateProfile
from app.db.models.user import User
from app.schemas.candidate import (
    CandidateProfileCreate,
    CandidateProfileUpdate,
    CandidateProfileResponse
)

router = APIRouter(prefix="/candidates", tags=["Candidate Master Profile"])

async def get_or_create_default_user(db: AsyncSession) -> User:
    """Helper to ensure a local user exists for local development without mandatory login."""
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            username="local_candidate",
            email="candidate@local.dev",
            hashed_password="local_dev_argon2_hash",
            is_active=True
        )
        db.add(user)
        await db.flush()
    return user

@router.post("/", response_model=CandidateProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate_profile(
    profile_in: CandidateProfileCreate,
    db: AsyncSession = Depends(get_db)
):
    """Creates a new Candidate Master Profile with verified facts."""
    user = await get_or_create_default_user(db)
    user_id = profile_in.user_id or user.id

    # Serialize items
    experience_data = [item.model_dump() for item in profile_in.verified_experience]
    education_data = [item.model_dump() for item in profile_in.verified_education]
    projects_data = [item.model_dump() for item in profile_in.learning_and_projects]

    profile = CandidateProfile(
        user_id=user_id,
        first_name=profile_in.first_name,
        last_name=profile_in.last_name,
        email=profile_in.email,
        phone=profile_in.phone,
        location_city=profile_in.location_city,
        location_country=profile_in.location_country,
        linkedin_url=profile_in.linkedin_url,
        github_url=profile_in.github_url,
        portfolio_url=profile_in.portfolio_url,
        verified_skills=profile_in.verified_skills,
        verified_experience=experience_data,
        verified_education=education_data,
        learning_and_projects=projects_data
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile

@router.get("/", response_model=List[CandidateProfileResponse])
async def list_candidate_profiles(db: AsyncSession = Depends(get_db)):
    """Lists all candidate profiles available locally."""
    result = await db.execute(select(CandidateProfile))
    return result.scalars().all()

@router.get("/{candidate_id}", response_model=CandidateProfileResponse)
async def get_candidate_profile(candidate_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves a specific Candidate Master Profile."""
    profile = await db.get(CandidateProfile, candidate_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate profile with ID '{candidate_id}' not found."
        )
    return profile

@router.put("/{candidate_id}", response_model=CandidateProfileResponse)
async def update_candidate_profile(
    candidate_id: str,
    update_in: CandidateProfileUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Updates candidate master profile facts."""
    profile = await db.get(CandidateProfile, candidate_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate profile with ID '{candidate_id}' not found."
        )

    update_data = update_in.model_dump(exclude_unset=True)

    # Process nested lists if present
    if "verified_experience" in update_data and update_data["verified_experience"] is not None:
        update_data["verified_experience"] = [
            item.model_dump() if hasattr(item, "model_dump") else item
            for item in update_data["verified_experience"]
        ]
    if "verified_education" in update_data and update_data["verified_education"] is not None:
        update_data["verified_education"] = [
            item.model_dump() if hasattr(item, "model_dump") else item
            for item in update_data["verified_education"]
        ]
    if "learning_and_projects" in update_data and update_data["learning_and_projects"] is not None:
        update_data["learning_and_projects"] = [
            item.model_dump() if hasattr(item, "model_dump") else item
            for item in update_data["learning_and_projects"]
        ]

    for key, val in update_data.items():
        setattr(profile, key, val)

    await db.commit()
    await db.refresh(profile)
    return profile

@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_candidate_profile(candidate_id: str, db: AsyncSession = Depends(get_db)):
    """Deletes a candidate master profile and all associated job profiles."""
    profile = await db.get(CandidateProfile, candidate_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate profile with ID '{candidate_id}' not found."
        )
    await db.delete(profile)
    await db.commit()
    return None
