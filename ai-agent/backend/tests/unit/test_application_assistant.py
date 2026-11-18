"""Unit tests for browser application assistance and approval safety."""

import pytest

from app.automation.application_assistant import ApplicationAssistant
from app.automation.approval_gate import ApplicationApprovalGate
from app.core.exceptions import InvalidApprovalTokenError


def test_application_preview_requires_contact_and_resume(tmp_path):
    candidate = type("Candidate", (), {
        "first_name": "",
        "last_name": "",
        "email": "",
        "phone": None,
        "linkedin_url": None,
        "github_url": None
    })()
    resume_version = type("ResumeVersion", (), {
        "id": "version-1",
        "tailored_json": {},
        "pdf_file_path": None,
        "docx_file_path": None
    })()
    job = type("Job", (), {
        "id": "job-1",
        "title": "Engineer",
        "company_name": "Example"
    })()

    preview = ApplicationAssistant.build_preview(
        candidate_profile=candidate,
        resume_version=resume_version,
        job=job,
        target_url="https://jobs.example/apply"
    )
    missing = ApplicationAssistant().validate_preview(preview)

    assert "first_name" in missing
    assert "last_name" in missing
    assert "email" in missing
    assert "resume_file" in missing


def test_preview_changes_invalidate_approval(tmp_path):
    gate = ApplicationApprovalGate(str(tmp_path / "approvals.sqlite3"))
    preview = {
        "job_id": "job-1",
        "fields": {"first_name": "Alex"},
    }
    gate.create_pending("approval-1", preview)
    token = gate.approve("approval-1", preview)

    changed_preview = {
        "job_id": "job-1",
        "fields": {"first_name": "Changed"},
    }
    with pytest.raises(InvalidApprovalTokenError, match="preview changed"):
        gate.consume("approval-1", token, changed_preview)


def test_approval_token_is_exactly_once(tmp_path):
    gate = ApplicationApprovalGate(str(tmp_path / "approvals.sqlite3"))
    preview = {
        "job_id": "job-1",
        "fields": {"email": "alex@example.com"},
    }
    gate.create_pending("approval-1", preview)
    token = gate.approve("approval-1", preview)

    gate.consume("approval-1", token, preview)
    with pytest.raises(InvalidApprovalTokenError, match="already consumed"):
        gate.consume("approval-1", token, preview)


def test_wrong_and_expired_tokens_are_rejected(tmp_path):
    gate = ApplicationApprovalGate(str(tmp_path / "approvals.sqlite3"))
    preview = {"job_id": "job-1", "fields": {}}
    gate.create_pending("approval-1", preview)
    token = gate.approve("approval-1", preview)

    with pytest.raises(InvalidApprovalTokenError, match="invalid"):
        gate.consume("approval-1", "hitl_wrong", preview)
    gate.consume("approval-1", token, preview)


def test_captcha_detection_covers_common_providers():
    assert ApplicationAssistant.detect_captcha(
        '<div class="g-recaptcha"></div>'
    )
    assert ApplicationAssistant.detect_captcha(
        '<script src="https://challenges.cloudflare.com/turnstile/v0/api.js"></script>'
    )
    assert not ApplicationAssistant.detect_captcha("<html><body>Career form</body></html>")
