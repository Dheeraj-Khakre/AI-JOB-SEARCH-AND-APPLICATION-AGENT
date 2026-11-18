"""Candidate Profile Model."""

from typing import List, Dict, Any, Optional
from sqlalchemy import String, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin, TimestampMixin

class CandidateProfile(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "candidate_profiles"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Location
    location_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location_country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Online Profiles
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    github_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    portfolio_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Verified Master Facts (Ground Truth for Anti-Hallucination)
    verified_skills: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    verified_experience: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    verified_education: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    # Strictly Segregated Learning & Personal Projects (Non-commercial)
    learning_and_projects: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="candidate_profiles")
    job_profiles: Mapped[List["JobProfile"]] = relationship(
        "JobProfile", back_populates="candidate_profile", cascade="all, delete-orphan"
    )
    resumes: Mapped[List["Resume"]] = relationship(
        "Resume", back_populates="candidate_profile", cascade="all, delete-orphan"
    )
