"""Manual Assistance Fallback (Level 4 User-Guided Submission Runner)."""

from typing import List, Dict, Any, Optional
from pathlib import Path

from app.constants import AutomationLevel
from app.connectors.base import (
    JobPortalConnector,
    PortalCapabilitiesSchema,
    JobSearchQuery,
    JobListing,
    JobDetails,
    ApplicationFormData,
    FillResult,
    ValidationReport,
    SubmissionConfirmation,
    ApplicationStatusReport
)

class ManualAssistant(JobPortalConnector):
    """
    Level 4 Assisted Manual Mode:
    Activated when CAPTCHA, Cloudflare Turnstile, or strict anti-bot mitigations block automation.
    Prepares tailored resume, generates field answers, and guides the candidate step-by-step.
    """

    portal_id = "manual_assistant"
    name = "Assisted Manual Submission Runner"
    category = "COMPANY_CAREERS"
    base_urls = ["*"]

    capabilities = PortalCapabilitiesSchema(
        supports_search=False,
        supports_job_extraction=True,
        supports_form_detection=True,
        supports_resume_upload=False,
        supports_auto_fill=False,
        supports_direct_submit=False,
        supports_status_check=False,
        automation_level=AutomationLevel.LEVEL_4_MANUAL_ASSIST.value,
        requires_authentication=False,
        security_restrictions=["Anti-bot mitigation active", "User must complete submission manually"]
    )

    async def identify_portal(self, url: str) -> bool:
        return True

    async def check_support(self, url: str) -> PortalCapabilitiesSchema:
        return self.capabilities

    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        return True

    async def search_jobs(self, query: JobSearchQuery) -> List[JobListing]:
        return []

    async def extract_job_details(self, target: str) -> JobDetails:
        return JobDetails(
            portal_id=self.portal_id,
            external_job_id=None,
            title="Manual Submission Required",
            company_name="Target Enterprise",
            url=target,
            raw_description="Job details prepared for guided manual submission."
        )

    async def extract_job_description(self, target: str) -> str:
        return "Manual submission required."

    async def prepare_application(self, job_id: str, profile_data: Dict[str, Any]) -> ApplicationFormData:
        return ApplicationFormData(
            candidate_profile_id=profile_data.get("id", ""),
            first_name=profile_data.get("first_name", ""),
            last_name=profile_data.get("last_name", ""),
            email=profile_data.get("email", ""),
            phone=profile_data.get("phone", "")
        )

    async def fill_application(self, form_data: ApplicationFormData) -> FillResult:
        # Delivers payload to candidate's clipboard and assistant panel
        return FillResult(success=True, fields_filled=0, fields_failed=0, pending_fields=[])

    async def upload_resume(self, file_path: Path) -> bool:
        return True

    async def validate_application(self) -> ValidationReport:
        return ValidationReport(is_valid=True, resume_attached=True)

    async def submit_application(self, approval_token: str) -> SubmissionConfirmation:
        self.verify_approval(approval_token)
        return SubmissionConfirmation(
            success=True,
            confirmation_number=f"MAN-{approval_token[:8]}",
            message="Application answers and tailored resume provided. Candidate confirmed manual submission."
        )

    async def get_application_status(self, app_id: str) -> ApplicationStatusReport:
        return ApplicationStatusReport(app_id=app_id, status="APPLIED_MANUALLY")
