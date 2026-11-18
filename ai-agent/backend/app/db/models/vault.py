"""Encrypted Credentials Metadata Model."""

from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin, TimestampMixin

class EncryptedCredentialsMetadata(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "encrypted_credentials_metadata"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    service_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    key_identifier: Mapped[str] = mapped_column(String(64), nullable=False)
    ciphertext_b64: Mapped[str] = mapped_column(Text, nullable=False)
    salt_b64: Mapped[str] = mapped_column(String(64), nullable=False)
    nonce_b64: Mapped[str] = mapped_column(String(64), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="credentials")
