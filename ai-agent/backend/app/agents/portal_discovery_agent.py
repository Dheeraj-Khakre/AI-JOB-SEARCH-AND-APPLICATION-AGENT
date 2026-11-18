"""Universal Portal Discovery Agent (Agent 2)."""

import re
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
import httpx

from app.constants import AutomationLevel
from app.connectors.registry import PortalConnectorRegistry

class PortalCapabilityReport:
    """Structured report assessing portal compatibility and security posture."""

    def __init__(
        self,
        portal_name: str,
        website: str,
        ats_provider: Optional[str],
        job_extraction_status: str,
        application_form_detection_status: str,
        resume_upload_support: bool,
        application_submission_support: bool,
        authentication_requirements: str,
        security_restrictions: List[str],
        unsupported_features: List[str],
        recommended_integration_approach: str,
        active_connector_id: Optional[str] = None
    ):
        self.portal_name = portal_name
        self.website = website
        self.ats_provider = ats_provider
        self.job_extraction_status = job_extraction_status
        self.application_form_detection_status = application_form_detection_status
        self.resume_upload_support = resume_upload_support
        self.application_submission_support = application_submission_support
        self.authentication_requirements = authentication_requirements
        self.security_restrictions = security_restrictions
        self.unsupported_features = unsupported_features
        self.recommended_integration_approach = recommended_integration_approach
        self.active_connector_id = active_connector_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portal_name": self.portal_name,
            "website": self.website,
            "ats_provider": self.ats_provider,
            "job_extraction_status": self.job_extraction_status,
            "application_form_detection_status": self.application_form_detection_status,
            "resume_upload_support": self.resume_upload_support,
            "application_submission_support": self.application_submission_support,
            "authentication_requirements": self.authentication_requirements,
            "security_restrictions": self.security_restrictions,
            "unsupported_features": self.unsupported_features,
            "recommended_integration_approach": self.recommended_integration_approach,
            "active_connector_id": self.active_connector_id
        }


class PortalDiscoveryAgent:
    """
    Agent 2: Universal Portal Discovery Agent.
    Inspects unknown URLs, fingerprints ATS signatures, analyzes forms,
    and produces a comprehensive 10-point Capability Report.
    """

    ATS_SIGNATURES = {
        "Greenhouse": [r"boards\.greenhouse\.io", r"api\.greenhouse\.io", r"gh_jid", r"grnh\.se"],
        "Lever": [r"jobs\.lever\.co", r"api\.lever\.co", r"lever-job"],
        "Workday": [r"myworkdayjobs\.com", r"myworkday\.com", r"wd3\.myworkday"],
        "SmartRecruiters": [r"smartrecruiters\.com", r"jobs\.smartrecruiters\.com"],
        "Ashby": [r"jobs\.ashbyhq\.com", r"ashbyhq\.com"],
        "iCIMS": [r"icims\.com", r"jobs\.icims\.com"],
        "Taleo": [r"taleo\.net", r"oraclecloud\.com/taleo"],
        "LinkedIn": [r"linkedin\.com/jobs", r"linkedin\.com"],
        "Naukri": [r"naukri\.com"]
    }

    SECURITY_SIGNATURES = {
        "Cloudflare Turnstile / Challenge": [r"challenges\.cloudflare\.com", r"cf-turnstile", r"cf-chl-widget"],
        "Google reCAPTCHA": [r"google\.com/recaptcha", r"g-recaptcha"],
        "hCaptcha": [r"hcaptcha\.com", r"h-captcha"],
        "Akamai Bot Manager": [r"akamaighost", r"_abck"],
        "Datadome": [r"datadome\.co", r"ct\.captcha-delivery\.com"]
    }

    @classmethod
    async def inspect_url(cls, target_url: str) -> PortalCapabilityReport:
        """
        Executes the 10-step inspection pipeline:
        1. Open & inspect URL
        2. Identify domain
        3. Detect ATS provider
        4. Detect security restrictions & bot mitigation
        5. Identify form fields & resume inputs
        6. Determine supported capabilities
        7. Match existing connector or fallback
        8. Synthesize capability report
        """
        parsed_url = urlparse(target_url)
        domain = parsed_url.netloc or target_url

        html_content = ""
        status_code = 0

        # Step 1: Fetch page content using lightweight HTTP client
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=12.0,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                    )
                }
            ) as client:
                resp = await client.get(target_url)
                status_code = resp.status_code
                html_content = resp.text
        except Exception:
            # Network issue or blocked by host
            pass

        # Step 2: Detect ATS provider
        detected_ats = None
        for ats_name, patterns in cls.ATS_SIGNATURES.items():
            for pat in patterns:
                if re.search(pat, target_url, re.IGNORECASE) or (html_content and re.search(pat, html_content, re.IGNORECASE)):
                    detected_ats = ats_name
                    break
            if detected_ats:
                break

        # Step 3: Detect security restrictions
        security_restrictions = []
        if html_content:
            for sec_name, sec_patterns in cls.SECURITY_SIGNATURES.items():
                for pat in sec_patterns:
                    if re.search(pat, html_content, re.IGNORECASE):
                        security_restrictions.append(sec_name)
                        break

        # Step 4: Analyze DOM if HTML is present
        has_file_input = False
        form_found = False
        job_extraction_ok = False
        auth_required = False

        if html_content:
            soup = BeautifulSoup(html_content, "html.parser")
            # Check form elements
            forms = soup.find_all("form")
            if forms:
                form_found = True
            file_inputs = soup.find_all("input", {"type": "file"})
            if file_inputs:
                has_file_input = True

            # Check job title / heading
            headings = soup.find_all(["h1", "h2"])
            if headings and len(html_content) > 500:
                job_extraction_ok = True

            # Check password or login fields
            if soup.find("input", {"type": "password"}):
                auth_required = True

        # Step 5: Resolve connector
        connector = await PortalConnectorRegistry.resolve_for_url(target_url)

        # Step 6: Determine recommended approach and unsupported features
        unsupported = []
        if security_restrictions:
            recommended_approach = (
                "LEVEL 4: Assisted Manual Submission. "
                "Automated submission is paused due to bot protection or CAPTCHA challenge."
            )
            submission_support = False
            unsupported.append("Automated headless form submission (requires manual candidate confirmation)")
        elif detected_ats in ["Greenhouse", "Lever"]:
            recommended_approach = (
                "LEVEL 2: ATS-Specific Integration. "
                "High compatibility: Structured extraction and automated form prefilling supported."
            )
            submission_support = True
        elif detected_ats == "Workday":
            recommended_approach = (
                "LEVEL 2: Workday Multi-step Wizard. "
                "Account creation and human review required at step threshold."
            )
            submission_support = False
            unsupported.append("1-Click Direct Submission (Workday multi-step account requirements)")
        elif detected_ats in ["LinkedIn", "Naukri"]:
            recommended_approach = (
                "LEVEL 3: Generic Browser Adapter. "
                "Prefill supported; requires final human approval."
            )
            submission_support = False
        else:
            recommended_approach = (
                "LEVEL 3 / LEVEL 4: Heuristic DOM Extraction. "
                "The site is unstandardized; inspect form fields before submission."
            )
            submission_support = False
            unsupported.append("Standardized ATS status checking")

        portal_display_name = detected_ats or domain.replace("www.", "").split(".")[0].capitalize()

        return PortalCapabilityReport(
            portal_name=f"{portal_display_name} Job Portal",
            website=f"{parsed_url.scheme}://{domain}",
            ats_provider=detected_ats or "Custom / Proprietary ATS",
            job_extraction_status="SUPPORTED" if (job_extraction_ok or status_code == 200) else "LIMITED",
            application_form_detection_status="DETECTED" if form_found else "NOT_DETECTED_ON_MAIN_PAGE",
            resume_upload_support=has_file_input or (detected_ats in ["Greenhouse", "Lever", "Workday"]),
            application_submission_support=submission_support,
            authentication_requirements="YES (Login Required)" if auth_required else "NO (Public Application)",
            security_restrictions=security_restrictions or ["None Detected"],
            unsupported_features=unsupported or ["None identified"],
            recommended_integration_approach=recommended_approach,
            active_connector_id=connector.portal_id if connector else "generic_browser"
        )
