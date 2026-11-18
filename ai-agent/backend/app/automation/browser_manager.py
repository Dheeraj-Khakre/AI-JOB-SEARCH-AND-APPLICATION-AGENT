"""Isolated Playwright browser context management."""

import secrets
from pathlib import Path
from typing import Any

from app.config import settings
from app.core.exceptions import AntiBotChallengeDetectedError, PortalConnectorError


class BrowserAutomationManager:
    """Creates a short-lived, profile-isolated Playwright browser context."""

    @staticmethod
    def _challenge_text(html: str) -> bool:
        lowered = html.lower()
        signatures = (
            "captcha",
            "cloudflare",
            "challenge-platform",
            "cf-turnstile",
            "hcaptcha",
            "recaptcha",
            "akamai",
            "datadome",
        )
        return any(signature in lowered for signature in signatures)

    async def open_application(
        self,
        target_url: str,
        session_id: str
    ) -> dict[str, Any]:
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise PortalConnectorError(
                "Playwright is not installed. Install backend requirements and "
                "run 'python -m playwright install chromium'."
            ) from exc

        profile_dir = (
            Path(settings.BROWSER_PROFILE_DIR)
            / f"application-{session_id}-{secrets.token_hex(6)}"
        )
        profile_dir.mkdir(parents=True, exist_ok=True)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=settings.PLAYWRIGHT_HEADLESS
            )
            context = await browser.new_context(
                user_agent=settings.BROWSER_USER_AGENT
            )
            page = await context.new_page()
            try:
                await page.goto(
                    target_url,
                    wait_until="domcontentloaded",
                    timeout=settings.PLAYWRIGHT_TIMEOUT_MS
                )
                html = await page.content()
                if self._challenge_text(html):
                    raise AntiBotChallengeDetectedError(
                        "Automation paused: CAPTCHA or anti-bot challenge detected.",
                        {"target_url": target_url}
                    )
                title = await page.title()
                return {
                    "status": "OPEN",
                    "target_url": page.url,
                    "title": title,
                    "profile_directory": str(profile_dir),
                }
            finally:
                await context.close()
                await browser.close()
