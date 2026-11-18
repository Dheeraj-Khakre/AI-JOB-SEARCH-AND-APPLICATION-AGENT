"""API tests for application HITL preparation and approval."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints.applications import get_db
from app.main import app


@pytest.mark.asyncio
async def test_application_prepare_and_rejects_ungrounded_resume(tmp_path):
    gate = __import__(
        "app.api.v1.endpoints.applications",
        fromlist=["approval_gate"]
    ).approval_gate
    gate.database_path = str(tmp_path / "approvals.sqlite3")
    gate._initialize()

    job = SimpleNamespace(
        id="job-1",
        title="Python Engineer",
        company_name="Example"
    )
    resume_version = SimpleNamespace(
        id="version-1",
        resume_id="resume-1",
        job_id="job-1",
        grounding_verified=False,
        tailored_json={},
        pdf_file_path=None,
        docx_file_path=None
    )

    db = SimpleNamespace(
        get=AsyncMock(side_effect=[job, resume_version]),
        execute=AsyncMock(),
        add=Mock(),
    )

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/applications/prepare",
                json={
                    "job_id": "job-1",
                    "resume_version_id": "version-1",
                    "target_url": "https://jobs.example/apply"
                }
            )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_application_prepare_approve_preview_binding(tmp_path):
    module = __import__(
        "app.api.v1.endpoints.applications",
        fromlist=["approval_gate", "ApplicationApprovalGate"]
    )
    gate = module.ApplicationApprovalGate(str(tmp_path / "approvals.sqlite3"))
    with patch(
        "app.api.v1.endpoints.applications.approval_gate",
        gate
    ):
        job = SimpleNamespace(
            id="job-1",
            title="Python Engineer",
            company_name="Example"
        )
        resume_version = SimpleNamespace(
            id="version-1",
            resume_id="resume-1",
            job_id="job-1",
            grounding_verified=True,
            tailored_json={
                "contact_info": {
                    "first_name": "Alex",
                    "last_name": "Engineer",
                    "email": "alex@example.com",
                    "phone": "+1-555-0100"
                }
            },
            pdf_file_path=str(tmp_path / "resume.pdf"),
            docx_file_path=None
        )
        (tmp_path / "resume.pdf").write_text("resume", encoding="utf-8")
        resume = SimpleNamespace(
            id="resume-1",
            candidate_profile_id="candidate-1"
        )
        candidate = SimpleNamespace(
            first_name="Alex",
            last_name="Engineer",
            email="alex@example.com",
            phone="+1-555-0100",
            linkedin_url=None,
            github_url=None
        )

        db = SimpleNamespace(
            get=AsyncMock(side_effect=[job, resume_version, resume, candidate]),
            execute=AsyncMock(return_value=SimpleNamespace(
                scalar_one_or_none=lambda: resume
            ))
        )

        async def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                prepared = await client.post(
                    "/api/v1/applications/prepare",
                    json={
                        "job_id": "job-1",
                        "resume_version_id": "version-1",
                        "target_url": "https://jobs.example/apply"
                    }
                )
                prepared_data = prepared.json()
                approved = await client.post(
                    f"/api/v1/applications/{prepared_data['approval_id']}/approve",
                    json={"preview": prepared_data["preview"]}
                )
        finally:
            app.dependency_overrides.pop(get_db, None)

    assert prepared.status_code == 200
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"
    assert approved.json()["approval_token"].startswith("hitl_")
