"""Resume and Resume Version Models."""

from typing import Dict, Any, Optional, List
from sqlalchemy import String, Text, Boolean, ForeignKey, JSON, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin, TimestampMixin

class Resume(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "resumes"

    candidate_profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)  # PDF, DOCX
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    is_master: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    candidate_profile: Mapped["CandidateProfile"] = relationship("CandidateProfile", back_populates="resumes")
    versions: Mapped[List["ResumeVersion"]] = relationship(
        "ResumeVersion", back_populates="resume", cascade="all, delete-orphan"
    )


class ResumeVersion(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "resume_versions"

    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    version_label: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "Google - AI Lead"
    tailored_text: Mapped[str] = mapped_column(Text, nullable=False)
    tailored_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    pdf_file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    docx_file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    ats_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    grounding_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    resume: Mapped["Resume"] = relationship("Resume", back_populates="versions")
