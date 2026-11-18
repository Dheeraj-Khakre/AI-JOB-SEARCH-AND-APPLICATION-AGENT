"""Integration tests for job discovery and JD analysis endpoints."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.agents.jd_analysis_agent import ParsedJDRequirements
from app.api.v1.endpoints.jobs import get_db
from app.db.models.job import JobMatch
from app.main import app


@pytest.mark.asyncio
async def test_job_match_uses_only_verified_candidate_facts():
    job = SimpleNamespace(id="job-1", title="Backend Engineer", company_name="Acme")
    profile = SimpleNamespace(
        id="profile-1",
        candidate_profile_id="candidate-1",
        target_skills=["Kubernetes"],
        min_years_experience=8
    )
    candidate = SimpleNamespace(
        verified_skills=["Python"],
        verified_experience=[]
    )
    db = SimpleNamespace(
        get=AsyncMock(side_effect=[job, profile, candidate]),
        execute=AsyncMock(
            side_effect=[
                SimpleNamespace(scalar_one_or_none=lambda: None),
                SimpleNamespace(scalar_one_or_none=lambda: None)
            ]
        ),
        add=Mock(side_effect=lambda record: setattr(
            record,
            "evaluated_at",
            datetime.now(timezone.utc)
        ) if isinstance(record, JobMatch) else None),
        commit=AsyncMock(),
        refresh=AsyncMock()
    )

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch(
            "app.api.v1.endpoints.jobs.JDAnalysisAgent.analyze_jd_text",
            new=AsyncMock(return_value=ParsedJDRequirements(
                mandatory_skills=["Kubernetes"],
                experience_years=5
            ))
        ), patch(
            "app.api.v1.endpoints.jobs._extract_job_description",
            new=AsyncMock(return_value="Required: Kubernetes and 5 years of experience.")
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.post("/api/v1/jobs/job-1/match/profile-1")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    result = response.json()
    assert result["missing_skills"] == ["Kubernetes"]
    assert result["matching_skills"] == []
    assert result["experience_match_score"] == 0


@pytest.mark.asyncio
async def test_stored_job_analysis_fetches_and_persists_real_description():
    job = SimpleNamespace(id="job-2", url="https://jobs.example/role", status="DISCOVERED")
    connector = SimpleNamespace(
        extract_job_description=AsyncMock(return_value="Python engineer, 4+ years of experience.")
    )
    db = SimpleNamespace(
        get=AsyncMock(return_value=job),
        execute=AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: None)),
        add=Mock(side_effect=lambda record: setattr(
            record,
            "analyzed_at",
            datetime.now(timezone.utc)
        )),
        commit=AsyncMock(),
        refresh=AsyncMock()
    )

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch(
            "app.api.v1.endpoints.jobs.PortalConnectorRegistry.resolve_for_url",
            new=AsyncMock(return_value=connector)
        ), patch(
            "app.api.v1.endpoints.jobs.JDAnalysisAgent.analyze_jd_text",
            new=AsyncMock(return_value=ParsedJDRequirements(
                mandatory_skills=["Python"],
                experience_years=4
            ))
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.post("/api/v1/jobs/job-2/analyze")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 200
    assert response.json()["mandatory_skills"] == ["Python"]
    connector.extract_job_description.assert_awaited_once_with(job.url)
    persisted_description = db.add.call_args.args[0]
    assert persisted_description.raw_description == "Python engineer, 4+ years of experience."
