"""Target Career Profile Model."""

from typing import List, Optional
from sqlalchemy import String, Integer, Numeric, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin, TimestampMixin
from app.constants import RemotePreference, EmploymentType

class JobProfile(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "job_profiles"

    candidate_profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    profile_name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_job_titles: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    target_skills: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    min_years_experience: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    preferred_industries: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    preferred_locations: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    remote_preference: Mapped[str] = mapped_column(String(32), default=RemotePreference.ANY.value, nullable=False)

    expected_salary_min: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    expected_salary_currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    employment_type: Mapped[str] = mapped_column(String(32), default=EmploymentType.FULL_TIME.value, nullable=False)
    education_requirements: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    candidate_profile: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="job_profiles")
