"""Unit Tests for Portal Connectors, Registry, and Approval Security."""

import pytest
from app.connectors.registry import PortalConnectorRegistry
from app.core.exceptions import ApprovalRequiredError

@pytest.mark.asyncio
async def test_portal_connector_registry_initialization():
    """Verify prebuilt connectors are registered and accessible."""
    connectors = PortalConnectorRegistry.list_connectors()
    assert len(connectors) >= 5

    portal_ids = [c["portal_id"] for c in connectors]
    assert "greenhouse" in portal_ids
    assert "lever" in portal_ids
    assert "workday" in portal_ids
    assert "linkedin" in portal_ids
    assert "naukri" in portal_ids

@pytest.mark.asyncio
async def test_dynamic_url_resolution():
    """Verify URLs are dynamically resolved to their respective specialized connectors."""
    # Greenhouse
    gh_conn = await PortalConnectorRegistry.resolve_for_url("https://boards.greenhouse.io/anthropic/jobs/401")
    assert gh_conn.portal_id == "greenhouse"

    # Lever
    lever_conn = await PortalConnectorRegistry.resolve_for_url("https://jobs.lever.co/spotify/a1b2c3d4")
    assert lever_conn.portal_id == "lever"

    # Workday
    wd_conn = await PortalConnectorRegistry.resolve_for_url("https://adobe.wd5.myworkdayjobs.com/external/job/1")
    assert wd_conn.portal_id == "workday"

    # LinkedIn
    li_conn = await PortalConnectorRegistry.resolve_for_url("https://www.linkedin.com/jobs/view/3829102")
    assert li_conn.portal_id == "linkedin"

    # Naukri
    nk_conn = await PortalConnectorRegistry.resolve_for_url("https://www.naukri.com/job-listings-python-dev-12345")
    assert nk_conn.portal_id == "naukri"

    # Custom / Unknown Careers Page
    generic_conn = await PortalConnectorRegistry.resolve_for_url("https://careers.acme-corp-custom.org/openings/99")
    assert generic_conn.portal_id == "generic_browser"

@pytest.mark.asyncio
async def test_human_approval_token_mandatory_on_submission():
    """Verify that submit_application rejects execution if human approval token is missing or invalid."""
    connector = PortalConnectorRegistry.get_connector("greenhouse")

    # Missing token
    with pytest.raises(ApprovalRequiredError) as exc_info:
        await connector.submit_application("")
    assert "Human-In-The-Loop approval token is mandatory" in str(exc_info.value)

    # Invalid token prefix
    with pytest.raises(ApprovalRequiredError):
        await connector.submit_application("unauthorized_token_xyz")

    # Valid token proceeds
    confirmation = await connector.submit_application("hitl_valid_token_1234567890abcdef")
    assert confirmation.success is True
    assert "GH-" in confirmation.confirmation_number
