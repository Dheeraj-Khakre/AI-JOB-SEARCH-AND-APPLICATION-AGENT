"""Universal Portal Connector Registry and Factory."""

from typing import Any, Dict, List

from app.connectors.ats.greenhouse import GreenhouseConnector
from app.connectors.ats.lever import LeverConnector
from app.connectors.ats.workday import WorkdayConnector
from app.connectors.base import JobPortalConnector
from app.connectors.generic.browser_adapter import GenericBrowserAdapter
from app.connectors.generic.manual_assistant import ManualAssistant
from app.connectors.platforms.linkedin import LinkedInConnector
from app.connectors.platforms.naukri import NaukriConnector
from app.core.exceptions import PortalConnectorError


class PortalConnectorRegistry:
    """Registry managing active portal connector instances and resolution."""

    _connectors: Dict[str, JobPortalConnector] = {}

    @classmethod
    def initialize(cls) -> None:
        """Seeds the registry with default prebuilt connectors."""
        if cls._connectors:
            return

        defaults: List[JobPortalConnector] = [
            GreenhouseConnector(),
            LeverConnector(),
            WorkdayConnector(),
            LinkedInConnector(),
            NaukriConnector(),
            GenericBrowserAdapter(),
            ManualAssistant()
        ]

        for c in defaults:
            cls.register(c)

    @classmethod
    def register(cls, connector: JobPortalConnector) -> None:
        """Registers a new or custom portal connector."""
        cls._connectors[connector.portal_id] = connector

    @classmethod
    def get_connector(cls, portal_id: str) -> JobPortalConnector:
        """Retrieves a connector by its unique portal ID."""
        cls.initialize()
        connector = cls._connectors.get(portal_id)
        if not connector:
            raise PortalConnectorError(f"No connector registered for portal ID: '{portal_id}'")
        return connector

    @classmethod
    def get_search_connectors(cls) -> List[JobPortalConnector]:
        """Returns registered connectors that support job searches."""
        cls.initialize()
        return [
            connector
            for connector in cls._connectors.values()
            if connector.capabilities.supports_search
        ]

    @classmethod
    async def resolve_for_url(cls, url: str) -> JobPortalConnector:
        """
        Dynamically inspects a target URL and returns the best matching connector.
        Prioritizes ATS engines, then specific platforms, falling back to Generic Browser.
        """
        cls.initialize()

        # Priority 1: ATS connectors
        for pid in ["greenhouse", "lever", "workday"]:
            conn = cls._connectors.get(pid)
            if conn and await conn.identify_portal(url):
                return conn

        # Priority 2: Platform connectors
        for pid in ["linkedin", "naukri"]:
            conn = cls._connectors.get(pid)
            if conn and await conn.identify_portal(url):
                return conn

        # Priority 3: Fallback generic browser
        return cls._connectors["generic_browser"]

    @classmethod
    def list_connectors(cls) -> List[Dict[str, Any]]:
        """Lists metadata of all registered portal connectors."""
        cls.initialize()
        return [
            {
                "portal_id": c.portal_id,
                "name": c.name,
                "category": c.category,
                "base_urls": c.base_urls,
                "capabilities": c.capabilities.model_dump(),
            }
            for c in cls._connectors.values()
            if c.portal_id not in ["generic_browser", "manual_assistant"]
        ]
