"""API tests for grounded resume optimization."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.endpoints.resumes import get_db
from app.main import app


@pytest.mark.asyncio
async def test_optimize_resume_api_persists_verified_version():
    candidate = SimpleNamespace(
        id="candidate-1",
        first_name="Alex",
        last_name="Engineer",
        email="alex@example.com",
        phone=None,
        location_city=None,
        location_country=None,
        linkedin_url=None,
        github_url=None,
        verified_skills=["Python", "FastAPI"],
        verified_experience=[],
        verified_education=[],
        learning_and_projects=[]
    )
    resume = SimpleNamespace(
        id="resume-1",
        candidate_profile_id="candidate-1",
        parsed_json={
            "skills": ["Python", "FastAPI"],
            "experience": [],
            "education": [],
            "projects": []
        },
        raw_text="Alex Engineer\nPython FastAPI"
    )
    job = SimpleNamespace(id="job-1", title="Python Engineer", company_name="Example")
    description = SimpleNamespace(
        extracted_mandatory_skills=["Python", "FastAPI"],
        extracted_optional_skills=[]
    )
    db = SimpleNamespace(
        get=AsyncMock(side_effect=[resume, candidate, job]),
        execute=AsyncMock(return_value=SimpleNamespace(
            scalar_one_or_none=lambda: description
        )),
        add=Mock(),
        commit=AsyncMock(),
        refresh=AsyncMock()
    )

    async def assign_version_id():
        version = db.add.call_args.args[0]
        version.id = "version-1"

    db.flush = AsyncMock(side_effect=assign_version_id)

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch(
            "app.api.v1.endpoints.resumes.ATSPdfGenerator.generate_pdf",
            return_value="/tmp/ver.pdf"
        ), patch(
            "app.api.v1.endpoints.resumes.ATSDocxGenerator.generate_docx",
            return_value="/tmp/ver.docx"
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/resumes/optimize",
                    json={
                        "resume_id": "resume-1",
                        "job_id": "job-1",
                        "version_label": "Example - Python Engineer"
                    }
                )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code in {200, 201}
