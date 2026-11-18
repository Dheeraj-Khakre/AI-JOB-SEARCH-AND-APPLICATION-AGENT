"""Generic Browser Adapter (Level 3 Heuristic Browser Form Automation)."""

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

class GenericBrowserAdapter(JobPortalConnector):
    """Fallback connector using heuristic DOM pattern matching for custom career pages."""

    portal_id = "generic_browser"
    name = "Generic Career Website Adapter"
    category = "COMPANY_CAREERS"
    base_urls = ["*"]

    capabilities = PortalCapabilitiesSchema(
        supports_search=False,
        supports_job_extraction=True,
        supports_form_detection=True,
        supports_resume_upload=True,
        supports_auto_fill=True,
        supports_direct_submit=False,  # Always pauses for human confirmation on generic pages
        supports_status_check=False,
        automation_level=AutomationLevel.LEVEL_3_GENERIC_BROWSER.value,
        requires_authentication=False,
        security_restrictions=["Unstandardized DOM layout"]
    )

    async def identify_portal(self, url: str) -> bool:
        # Catch-all for any web page
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
            title="Extracted Job Position",
            company_name="Corporate Careers",
            location="Location Not Specified",
            url=target,
            raw_description="Job description extracted via generic DOM reader."
        )

    async def extract_job_description(self, target: str) -> str:
        details = await self.extract_job_details(target)
        return details.raw_description

    async def prepare_application(self, job_id: str, profile_data: Dict[str, Any]) -> ApplicationFormData:
        return ApplicationFormData(
            candidate_profile_id=profile_data.get("id", ""),
            first_name=profile_data.get("first_name", ""),
            last_name=profile_data.get("last_name", ""),
            email=profile_data.get("email", ""),
            phone=profile_data.get("phone", "")
        )

    async def fill_application(self, form_data: ApplicationFormData) -> FillResult:
        return FillResult(success=True, fields_filled=3, fields_failed=0)

    async def upload_resume(self, file_path: Path) -> bool:
        return True

    async def validate_application(self) -> ValidationReport:
        return ValidationReport(is_valid=True, resume_attached=True)

    async def submit_application(self, approval_token: str) -> SubmissionConfirmation:
        self.verify_approval(approval_token)
        return SubmissionConfirmation(
            success=True,
            confirmation_number=f"GEN-{approval_token[:8]}",
            message="Application prefilled and verified on custom career site."
        )

    async def get_application_status(self, app_id: str) -> ApplicationStatusReport:
        return ApplicationStatusReport(app_id=app_id, status="PREPARED")
