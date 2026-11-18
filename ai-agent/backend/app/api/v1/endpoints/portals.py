"""Portal Registry & Unknown Portal Discovery API Endpoints."""

from typing import List
from fastapi import APIRouter, HTTPException, status

from app.connectors.registry import PortalConnectorRegistry
from app.agents.portal_discovery_agent import PortalDiscoveryAgent
from app.schemas.portal import (
    PortalInfoResponse,
    URLInspectRequest,
    PortalCapabilityReportResponse
)

router = APIRouter(prefix="/portals", tags=["Portal Registry & Discovery"])

@router.get("/", response_model=List[PortalInfoResponse])
async def list_registered_portals():
    """Returns all registered career portal connectors and capability matrices."""
    connectors = PortalConnectorRegistry.list_connectors()
    return [PortalInfoResponse(**c) for c in connectors]

@router.get("/{portal_id}", response_model=PortalInfoResponse)
async def get_portal_connector(portal_id: str):
    """Retrieves operational details of a specific portal connector."""
    try:
        conn = PortalConnectorRegistry.get_connector(portal_id)
        return PortalInfoResponse(
            portal_id=conn.portal_id,
            name=conn.name,
            category=conn.category,
            base_urls=conn.base_urls,
            capabilities=conn.capabilities
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.post("/inspect", response_model=PortalCapabilityReportResponse)
async def inspect_unknown_portal_url(request: URLInspectRequest):
    """
    Agent 2: Inspects any job posting URL, detects ATS provider, evaluates form schema,
    and returns a structured 10-point Capability Report.
    """
    if not request.url or not request.url.startswith("http"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid HTTP or HTTPS URL is required for inspection."
        )

    report = await PortalDiscoveryAgent.inspect_url(request.url)
    return PortalCapabilityReportResponse(**report.to_dict())
