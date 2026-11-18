"""Portal Registry and Portal Capabilities Database Models."""

from typing import List, Dict, Any, Optional
from sqlalchemy import String, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin, TimestampMixin
from app.constants import AutomationLevel

class PortalRegistry(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "portal_registry"

    portal_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)  # INDIAN, INTERNATIONAL_ATS, COMPANY_CAREERS
    base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    connector_class: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    capabilities: Mapped[Optional["PortalCapabilities"]] = relationship(
        "PortalCapabilities", back_populates="portal", uselist=False, cascade="all, delete-orphan"
    )


class PortalCapabilities(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "portal_capabilities"

    portal_registry_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("portal_registry.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    supports_search: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_job_extraction: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    supports_form_detection: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    supports_resume_upload: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_auto_fill: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_direct_submit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_status_check: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    automation_level: Mapped[str] = mapped_column(
        String(32), default=AutomationLevel.LEVEL_4_MANUAL_ASSIST.value, nullable=False
    )
    requires_authentication: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    security_restrictions: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

    portal: Mapped["PortalRegistry"] = relationship("PortalRegistry", back_populates="capabilities")
