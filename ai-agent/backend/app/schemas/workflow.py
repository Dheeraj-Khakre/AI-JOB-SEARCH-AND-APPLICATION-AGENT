"""Request and response schemas for checkpointed agent workflows."""

from typing import Any, Literal
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, Field, model_validator


class WorkflowStartRequest(BaseModel):
    mode: Literal["discover", "inspect", "analyze", "optimize"]
    session_id: UUID | None = None
    active_job_profile_id: str | None = Field(default=None, min_length=1, max_length=36)
    selected_job_id: str | None = Field(default=None, min_length=1, max_length=36)
    target_url: AnyHttpUrl | None = None
    raw_jd_text: str | None = Field(default=None, min_length=20, max_length=20000)
    resume_id: str | None = Field(default=None, min_length=1, max_length=36)
    require_human_approval: bool = False

    @model_validator(mode="after")
    def validate_mode_inputs(self):
        if self.raw_jd_text is not None and len(self.raw_jd_text.strip()) < 20:
            raise ValueError("raw_jd_text must contain at least 20 non-whitespace characters.")
        if self.mode == "discover" and not self.active_job_profile_id:
            raise ValueError("active_job_profile_id is required for discovery.")
        if self.mode == "inspect" and not self.target_url:
            raise ValueError("target_url is required for portal inspection.")
        if self.mode == "analyze" and not (self.selected_job_id or self.raw_jd_text):
            raise ValueError("analyze mode requires selected_job_id or raw_jd_text.")
        if self.mode == "optimize" and not (
            self.resume_id and self.selected_job_id
        ):
            raise ValueError("optimize mode requires resume_id and selected_job_id.")
        return self


class WorkflowResumeRequest(BaseModel):
    decision: Literal["approve", "reject"]


class WorkflowResponse(BaseModel):
    session_id: UUID
    workflow_status: str
    current_agent: str | None = None
    iteration_count: int = 0
    state: dict[str, Any] = Field(default_factory=dict)
    pending_interrupt: dict[str, Any] | None = None
