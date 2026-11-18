"""Integration Tests for Portal Registry and URL Inspection Endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_list_portals_endpoint():
    """Verify GET /api/v1/portals/ returns all registered connectors with capability flags."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/portals/")
        assert res.status_code == 200
        portals = res.json()
        assert len(portals) >= 5
        ids = [p["portal_id"] for p in portals]
        assert "greenhouse" in ids
        assert "lever" in ids
        assert "linkedin" in ids

        # Check capabilities block
        gh = next(p for p in portals if p["portal_id"] == "greenhouse")
        assert gh["capabilities"]["supports_job_extraction"] is True
        assert gh["capabilities"]["automation_level"] == "LEVEL_2_ATS_INTEGRATION"

@pytest.mark.asyncio
async def test_get_single_portal_endpoint():
    """Verify GET /api/v1/portals/{portal_id}."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/portals/naukri")
        assert res.status_code == 200
        data = res.json()
        assert data["portal_id"] == "naukri"
        assert data["category"] == "INDIAN"

@pytest.mark.asyncio
async def test_inspect_portal_endpoint():
    """Verify POST /api/v1/portals/inspect executes Agent 2 discovery and returns 10-point report."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"url": "https://boards.greenhouse.io/figma/jobs/987654"}
        res = await client.post("/api/v1/portals/inspect", json=payload)
        assert res.status_code == 200
        report = res.json()
        assert report["ats_provider"] == "Greenhouse"
        assert report["active_connector_id"] == "greenhouse"
        assert report["job_extraction_status"] in ["SUPPORTED", "LIMITED"]
        assert "Greenhouse" in report["portal_name"]
