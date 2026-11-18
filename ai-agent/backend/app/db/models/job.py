"""Job Listing, Job Description, and Job Match Models."""

from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import String, Text, Numeric, ForeignKey, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin, TimestampMixin

class Job(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "jobs"

    portal_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    external_job_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    url: Mapped[str] = mapped_column(String(1024), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    employment_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    salary_range: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    posted_date: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="DISCOVERED", nullable=False)  # DISCOVERED, PROCESSED, APPLIED, ARCHIVED

    # Relationships
    description: Mapped[Optional["JobDescription"]] = relationship(
        "JobDescription", back_populates="job", uselist=False, cascade="all, delete-orphan"
    )
    matches: Mapped[List["JobMatch"]] = relationship(
        "JobMatch", back_populates="job", cascade="all, delete-orphan"
    )


class JobDescription(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "job_descriptions"

    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    raw_description: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_mandatory_skills: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    extracted_optional_skills: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    extracted_experience_years: Mapped[Optional[float]] = mapped_column(Numeric(4, 1), nullable=True)
    extracted_responsibilities: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    extracted_ats_keywords: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    extracted_interview_topics: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="description")


class JobMatch(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "job_matches"

    job_profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("job_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    overall_match_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)  # 0.0 to 100.0
    skills_match_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    experience_match_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    matching_skills: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    missing_skills: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="matches")
