"""Playwright browser automation and application approval."""

from app.automation.application_assistant import ApplicationAssistant
from app.automation.approval_gate import ApplicationApprovalGate
from app.automation.browser_manager import BrowserAutomationManager

__all__ = [
    "ApplicationAssistant",
    "ApplicationApprovalGate",
    "BrowserAutomationManager",
]
