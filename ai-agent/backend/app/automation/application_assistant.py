"""Browser-based application preparation and protected submission."""

from pathlib import Path
from typing import Any

from app.core.exceptions import (
    AntiBotChallengeDetectedError,
    PortalConnectorError,
)


class ApplicationAssistant:
    """Validates and previews application fields before protected submission."""

    CAPTCHA_SIGNATURES = (
        "captcha",
        "cloudflare",
        "cf-turnstile",
        "hcaptcha",
        "recaptcha",
        "akamai",
        "datadome",
    )

    @staticmethod
    def build_preview(
        candidate_profile: Any,
        resume_version: Any,
        job: Any,
        target_url: str
    ) -> dict[str, Any]:
        tailored = resume_version.tailored_json or {}
        contact = tailored.get("contact_info") or {}
        fields = {
            "first_name": contact.get("first_name")
            or candidate_profile.first_name,
            "last_name": contact.get("last_name")
            or candidate_profile.last_name,
            "email": contact.get("email") or candidate_profile.email,
            "phone": contact.get("phone") or getattr(candidate_profile, "phone", None),
            "linkedin_url": contact.get("linkedin_url")
            or getattr(candidate_profile, "linkedin_url", None),
            "github_url": contact.get("github_url")
            or getattr(candidate_profile, "github_url", None),
        }
        return {
            "job_id": job.id,
            "job_title": job.title,
            "company_name": job.company_name,
            "target_url": target_url,
            "resume_version_id": resume_version.id,
            "resume_file": resume_version.pdf_file_path
            or resume_version.docx_file_path,
            "fields": fields,
        }

    @classmethod
    def validate_preview(cls, preview: dict[str, Any]) -> list[str]:
        missing: list[str] = []
        fields = preview.get("fields", {})
        for field in ("first_name", "last_name", "email"):
            if not fields.get(field):
                missing.append(field)
        resume_file = preview.get("resume_file")
        if not resume_file or not Path(str(resume_file)).is_file():
            missing.append("resume_file")
        return missing

    @staticmethod
    def detect_captcha(html: str) -> bool:
        lowered = html.lower()
        return any(signature in lowered for signature in (
            "captcha",
            "cloudflare",
            "cf-turnstile",
            "hcaptcha",
            "recaptcha",
            "akamai",
            "datadome",
        ))

    async def submit(
        self,
        target_url: str,
        preview: dict[str, Any],
        approval_id: str,
        approval_token: str,
        approval_gate: Any
    ) -> dict[str, Any]:
        missing = self.validate_preview(preview)
        if missing:
            raise PortalConnectorError(
                f"Application is incomplete: missing {', '.join(missing)}."
            )

        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise PortalConnectorError(
                "Playwright is not installed for application submission."
            ) from exc

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            try:
                await page.goto(
                    target_url,
                    wait_until="domcontentloaded",
                    timeout=30000
                )
                html = await page.content()
                if self.detect_captcha(html):
                    # Keep the approval token available for a later clean page;
                    # do not consume it on anti-bot challenge.
                    raise AntiBotChallengeDetectedError(
                        "Submission blocked: CAPTCHA or anti-bot challenge detected."
                    )

                submit_selector = (
                    "button[type='submit'], input[type='submit'], "
                    "button:has-text('Submit'), button:has-text('Apply')"
                )
                submit_buttons = page.locator(submit_selector)
                if await submit_buttons.count() == 0:
                    raise PortalConnectorError(
                        "No submit control was found. Application was not submitted."
                    )

                # Phase 9 deliberately stops before irreversible submission.
                # The framework will call click() only in an explicitly guarded
                # future portal-specific implementation.
                approval_gate.consume(approval_id, approval_token, preview)
                raise PortalConnectorError(
                    "Submission stopped at the final submit control. "
                    "No portal submission was executed."
                )
            finally:
                await context.close()
                await browser.close()
