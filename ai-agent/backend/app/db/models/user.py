"""User Model."""

from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List

from app.db.base import Base, UUIDMixin, TimestampMixin

class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    candidate_profiles: Mapped[List["CandidateProfile"]] = relationship(
        "CandidateProfile", back_populates="user", cascade="all, delete-orphan"
    )
    credentials: Mapped[List["EncryptedCredentialsMetadata"]] = relationship(
        "EncryptedCredentialsMetadata", back_populates="user", cascade="all, delete-orphan"
    )
