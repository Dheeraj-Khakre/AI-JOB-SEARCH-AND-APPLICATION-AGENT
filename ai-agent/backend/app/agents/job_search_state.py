"""Typed state shared by the job-search workflow graph."""

from typing import Any, Literal, TypedDict

WorkflowMode = Literal["discover", "inspect", "analyze", "optimize"]
ApprovalStatus = Literal["IDLE", "AWAITING_REVIEW", "APPROVED", "REJECTED"]


class JobSearchAppState(TypedDict, total=False):
    session_id: str
    user_id: str
    mode: WorkflowMode
    active_job_profile_id: str
    resume_id: str
    selected_job_id: str
    target_url: str
    raw_jd_text: str
    require_human_approval: bool

    discovered_jobs: list[dict[str, Any]]
    current_portal_report: dict[str, Any]
    analyzed_jd: dict[str, Any]
    compatibility_score: float
    candidate_master_facts: dict[str, Any]
    active_resume_version_id: str
    tailored_resume_data: dict[str, Any]
    grounding_verified: bool
    generated_pdf_path: str
    generated_docx_path: str
    application_id: str
    prefilled_form_fields: dict[str, Any]
    match_result: dict[str, Any]
    approval_summary: dict[str, Any]
    approval_status: ApprovalStatus
    submission_confirmation: dict[str, Any]
    interview_session_id: str
    interview_questions: list[dict[str, Any]]

    current_agent: str
    agent_history: list[str]
    iteration_count: int
    workflow_status: str
    error_message: str
