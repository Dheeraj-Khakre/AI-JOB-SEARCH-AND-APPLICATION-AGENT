"""Portal and URL Inspection Pydantic Schemas."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl

from app.connectors.base import PortalCapabilitiesSchema

class PortalInfoResponse(BaseModel):
    portal_id: str
    name: str
    category: str
    base_urls: List[str]
    capabilities: PortalCapabilitiesSchema

class URLInspectRequest(BaseModel):
    url: str = Field(..., description="Target job posting or career website URL to inspect")

class PortalCapabilityReportResponse(BaseModel):
    portal_name: str
    website: str
    ats_provider: Optional[str]
    job_extraction_status: str
    application_form_detection_status: str
    resume_upload_support: bool
    application_submission_support: bool
    authentication_requirements: str
    security_restrictions: List[str]
    unsupported_features: List[str]
    recommended_integration_approach: str
    active_connector_id: Optional[str]

class RegisterCustomConnectorRequest(BaseModel):
    portal_id: str = Field(..., min_length=2, max_length=64)
    name: str = Field(..., min_length=2, max_length=128)
    category: str = Field(default="COMPANY_CAREERS")
    base_urls: List[str]
    automation_level: str = "LEVEL_3_GENERIC_BROWSER"
