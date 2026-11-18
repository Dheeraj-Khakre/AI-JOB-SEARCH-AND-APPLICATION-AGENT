"""Schemas for browser application assistance and HITL approval."""

from typing import Any

from pydantic import BaseModel, Field


class ApplicationPrepareRequest(BaseModel):
    job_id: str = Field(..., min_length=1, max_length=36)
    resume_version_id: str = Field(..., min_length=1, max_length=36)
    target_url: str = Field(..., min_length=8, max_length=2048)


class ApplicationPrepareResponse(BaseModel):
    approval_id: str
    status: str
    expires_in_seconds: int
    preview: dict[str, Any]
    missing_fields: list[str]
    approval_token: str | None = None


class ApplicationApproveRequest(BaseModel):
    preview: dict[str, Any]


class ApplicationSubmitRequest(BaseModel):
    approval_token: str = Field(..., min_length=5, max_length=256)
    preview: dict[str, Any]
