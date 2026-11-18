"""Unit Tests for Universal Portal Discovery Agent (Agent 2)."""

import pytest
from app.agents.portal_discovery_agent import PortalDiscoveryAgent

@pytest.mark.asyncio
async def test_portal_discovery_greenhouse_url():
    """Verify inspection and report generation on Greenhouse URL."""
    url = "https://boards.greenhouse.io/stripe/jobs/5432100"
    report = await PortalDiscoveryAgent.inspect_url(url)

    assert report.ats_provider == "Greenhouse"
    assert report.active_connector_id == "greenhouse"
    assert "LEVEL 2: ATS-Specific Integration" in report.recommended_integration_approach
    assert report.resume_upload_support is True

@pytest.mark.asyncio
async def test_portal_discovery_workday_url():
    """Verify inspection on Workday URL recognizes multi-step wizard restrictions."""
    url = "https://salesforce.wd12.myworkdayjobs.com/External_Career_Site/job/1"
    report = await PortalDiscoveryAgent.inspect_url(url)

    assert report.ats_provider == "Workday"
    assert report.active_connector_id == "workday"
    assert "Multi-step" in report.recommended_integration_approach or "Workday" in report.recommended_integration_approach

@pytest.mark.asyncio
async def test_portal_discovery_unknown_site():
    """Verify inspection on unknown custom domain generates capability report with recommended approach."""
    url = "https://innovative-startup-careers.io/apply/engineer"
    report = await PortalDiscoveryAgent.inspect_url(url)

    assert report.portal_name is not None
    assert report.website == "https://innovative-startup-careers.io"
    assert report.active_connector_id == "generic_browser"
    assert report.application_submission_support is False  # Safe default: no direct submit on unverified sites
