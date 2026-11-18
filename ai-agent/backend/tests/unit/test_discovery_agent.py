"""Unit Tests for Job Discovery Agent (Agent 1)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.agents.discovery_agent import JobDiscoveryAgent
from app.connectors.base import JobListing
from app.connectors.registry import PortalConnectorRegistry
from app.core.exceptions import PortalConnectorError


def test_canonical_hash_deduplication():
    """Canonical hashes ignore casing and whitespace differences."""
    title_1 = "Senior Python Developer"
    company_1 = "TechCorp Inc."
    url_1 = "https://www.linkedin.com/jobs/view/1001"

    title_2 = "senior python developer "
    company_2 = "techcorp inc"
    url_2 = "https://www.naukri.com/job-listings-1002"

    hash_1 = JobDiscoveryAgent.compute_canonical_hash(title_1, company_1, url_1)
    hash_2 = JobDiscoveryAgent.compute_canonical_hash(title_2, company_2, url_2)

    assert hash_1 == hash_2

def test_canonical_hash_distinguishes_different_roles():
    """Verify distinct roles produce different hashes."""
    h_dev = JobDiscoveryAgent.compute_canonical_hash("Python Engineer", "Acme", "https://site/1")
    h_pm = JobDiscoveryAgent.compute_canonical_hash("Product Manager", "Acme", "https://site/2")
    assert h_dev != h_pm

def test_canonical_hash_includes_location_when_available():
    remote = JobDiscoveryAgent.compute_canonical_hash("Python Engineer", "Acme", location="Remote")
    onsite = JobDiscoveryAgent.compute_canonical_hash("Python Engineer", "Acme", location="London")
    assert remote != onsite

@pytest.mark.asyncio
async def test_discovery_searches_all_search_capable_connectors_and_deduplicates():
    listing_linkedin = JobListing(
        portal_id="linkedin",
        title="Senior Python Developer",
        company_name="TechCorp Inc.",
        location="Remote",
        url="https://linkedin.example/jobs/1"
    )
    listing_other_portal = JobListing(
        portal_id="other",
        title="senior python developer ",
        company_name="techcorp inc",
        location="Remote",
        url="https://other.example/jobs/2"
    )
    connectors = [
        SimpleNamespace(
            portal_id="linkedin",
            search_jobs=AsyncMock(return_value=[listing_linkedin])
        ),
        SimpleNamespace(
            portal_id="other",
            search_jobs=AsyncMock(return_value=[listing_other_portal])
        )
    ]
    db = SimpleNamespace(
        execute=AsyncMock(return_value=SimpleNamespace(all=lambda: [])),
        add=Mock(),
        commit=AsyncMock(),
        refresh=AsyncMock()
    )
    profile = SimpleNamespace(
        target_job_titles=["Senior Python Developer"],
        target_skills=["Python"],
        preferred_locations=["Remote"],
        remote_preference="REMOTE",
        min_years_experience=5
    )

    with patch.object(PortalConnectorRegistry, "get_search_connectors", return_value=connectors):
        jobs = await JobDiscoveryAgent.discover_jobs(profile, db)

    assert len(jobs) == 1
    assert jobs[0].portal_id == "linkedin"
    assert db.add.call_count == 1
    for connector in connectors:
        connector.search_jobs.assert_awaited_once()
        assert connector.search_jobs.await_args.args[0].remote is True

@pytest.mark.asyncio
async def test_discovery_skips_jobs_already_stored_under_another_url():
    listing = JobListing(
        portal_id="naukri",
        title="Python Engineer",
        company_name="Acme",
        location="Remote",
        url="https://naukri.example/jobs/2"
    )
    connector = SimpleNamespace(portal_id="naukri", search_jobs=AsyncMock(return_value=[listing]))
    existing_job = SimpleNamespace(
        title=" python-engineer ",
        company_name="ACME",
        url="https://other.example/jobs/1",
        location="REMOTE"
    )
    db = SimpleNamespace(
        execute=AsyncMock(return_value=SimpleNamespace(all=lambda: [
            (existing_job.title, existing_job.company_name, existing_job.url, existing_job.location)
        ])),
        add=Mock(),
        commit=AsyncMock(),
        refresh=AsyncMock()
    )
    profile = SimpleNamespace(
        target_job_titles=["Python Engineer"],
        target_skills=[],
        preferred_locations=[],
        remote_preference="ANY",
        min_years_experience=0
    )

    with patch.object(PortalConnectorRegistry, "get_search_connectors", return_value=[connector]):
        jobs = await JobDiscoveryAgent.discover_jobs(profile, db)

    assert jobs == []
    db.add.assert_not_called()
    db.commit.assert_not_awaited()
    assert connector.search_jobs.await_args.args[0].remote is False

@pytest.mark.asyncio
async def test_discovery_raises_when_every_connector_fails():
    connector = SimpleNamespace(
        portal_id="broken",
        search_jobs=AsyncMock(side_effect=RuntimeError("portal unavailable"))
    )
    profile = SimpleNamespace(
        target_job_titles=["Python Engineer"],
        target_skills=[],
        preferred_locations=[],
        remote_preference="ANY",
        min_years_experience=0
    )
    db = SimpleNamespace()

    with patch.object(PortalConnectorRegistry, "get_search_connectors", return_value=[connector]):
        with pytest.raises(PortalConnectorError, match="all 1"):
            await JobDiscoveryAgent.discover_jobs(profile, db)

@pytest.mark.asyncio
async def test_discovery_keeps_successful_portal_results_when_another_fails(caplog):
    listing = JobListing(
        portal_id="working",
        title="Python Engineer",
        company_name="Acme",
        url="https://working.example/jobs/1"
    )
    connectors = [
        SimpleNamespace(
            portal_id="working",
            search_jobs=AsyncMock(return_value=[listing])
        ),
        SimpleNamespace(
            portal_id="offline",
            search_jobs=AsyncMock(side_effect=RuntimeError("portal unavailable"))
        )
    ]
    db = SimpleNamespace(
        execute=AsyncMock(return_value=SimpleNamespace(all=lambda: [])),
        add=Mock(),
        commit=AsyncMock(),
        refresh=AsyncMock()
    )
    profile = SimpleNamespace(
        target_job_titles=["Python Engineer"],
        target_skills=[],
        preferred_locations=[],
        remote_preference="ANY",
        min_years_experience=0
    )

    with patch.object(PortalConnectorRegistry, "get_search_connectors", return_value=connectors):
        jobs = await JobDiscoveryAgent.discover_jobs(profile, db)

    assert len(jobs) == 1
    assert "offline" in caplog.text
