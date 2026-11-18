"""Universal Job Portal Connector Abstract Base Class and Data Models."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field

from app.constants import AutomationLevel
from app.core.exceptions import PortalConnectorError, ApprovalRequiredError

class PortalCapabilitiesSchema(BaseModel):
    supports_search: bool = False
    supports_job_extraction: bool = True
    supports_form_detection: bool = True
    supports_resume_upload: bool = False
    supports_auto_fill: bool = False
    supports_direct_submit: bool = False
    supports_status_check: bool = False
    automation_level: str = AutomationLevel.LEVEL_4_MANUAL_ASSIST.value
    requires_authentication: bool = False
    security_restrictions: List[str] = Field(default_factory=list)

class JobSearchQuery(BaseModel):
    role_titles: List[str]
    skills: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    remote: bool = False
    experience_years_min: int = 0
    limit: int = 25

class JobListing(BaseModel):
    portal_id: str
    external_job_id: Optional[str] = None
    title: str
    company_name: str
    location: Optional[str] = None
    url: str
    employment_type: Optional[str] = None
    salary_range: Optional[str] = None
    posted_date: Optional[str] = None

class JobDetails(JobListing):
    raw_description: str
    skills_detected: List[str] = Field(default_factory=list)
    experience_detected: Optional[float] = None
    apply_url: Optional[str] = None

class ApplicationFormData(BaseModel):
    candidate_profile_id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    resume_file_path: Optional[str] = None
    cover_letter_text: Optional[str] = None
    custom_field_answers: Dict[str, str] = Field(default_factory=dict)

class FillResult(BaseModel):
    success: bool
    fields_filled: int
    fields_failed: int
    pending_fields: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None

class ValidationReport(BaseModel):
    is_valid: bool
    missing_mandatory_fields: List[str] = Field(default_factory=list)
    resume_attached: bool = False
    captcha_present: bool = False
    warnings: List[str] = Field(default_factory=list)

class SubmissionConfirmation(BaseModel):
    success: bool
    confirmation_number: Optional[str] = None
    submitted_at: Optional[str] = None
    message: str
    screenshot_path: Optional[str] = None

class ApplicationStatusReport(BaseModel):
    app_id: str
    status: str
    last_updated: Optional[str] = None
    notes: Optional[str] = None


class JobPortalConnector(ABC):
    """
    Abstract Base Class for all Job Board, ATS, and Career Website Connectors.
    Implements a strict 4-level capability framework.
    """

    portal_id: str
    name: str
    category: str  # "INDIAN", "INTERNATIONAL_ATS", "COMPANY_CAREERS"
    base_urls: List[str]
    capabilities: PortalCapabilitiesSchema

    @abstractmethod
    async def identify_portal(self, url: str) -> bool:
        """Determines if the given URL is hosted or handled by this connector."""
        pass

    @abstractmethod
    async def check_support(self, url: str) -> PortalCapabilitiesSchema:
        """Evaluates operational support and restrictions for the given URL."""
        pass

    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Handles authentication using encrypted credentials or browser session."""
        pass

    @abstractmethod
    async def search_jobs(self, query: JobSearchQuery) -> List[JobListing]:
        """Searches for jobs matching role, location, and experience criteria."""
        pass

    @abstractmethod
    async def extract_job_details(self, target: str) -> JobDetails:
        """Extracts structured metadata (title, company, description, apply link)."""
        pass

    @abstractmethod
    async def extract_job_description(self, target: str) -> str:
        """Extracts clean, unformatted raw job description text."""
        pass

    @abstractmethod
    async def prepare_application(self, job_id: str, profile_data: Dict[str, Any]) -> ApplicationFormData:
        """Pre-maps candidate profile data to portal form fields."""
        pass

    @abstractmethod
    async def fill_application(self, form_data: ApplicationFormData) -> FillResult:
        """Fills detected form fields using browser automation."""
        pass

    @abstractmethod
    async def upload_resume(self, file_path: Path) -> bool:
        """Uploads tailored resume document to the application file input."""
        pass

    @abstractmethod
    async def validate_application(self) -> ValidationReport:
        """Validates that all mandatory fields are filled and errors are cleared."""
        pass

    @abstractmethod
    async def submit_application(self, approval_token: str) -> SubmissionConfirmation:
        """Submits the application form after validating human approval token."""
        pass

    @abstractmethod
    async def get_application_status(self, app_id: str) -> ApplicationStatusReport:
        """Checks latest status of a submitted application if supported."""
        pass

    def verify_approval(self, approval_token: str) -> None:
        """Security guardrail ensuring human approval token is present before submission."""
        if not approval_token or not approval_token.startswith("hitl_"):
            raise ApprovalRequiredError(
                f"Application submission on '{self.name}' was blocked. "
                "Human-In-The-Loop approval token is mandatory before any form submission."
            )
