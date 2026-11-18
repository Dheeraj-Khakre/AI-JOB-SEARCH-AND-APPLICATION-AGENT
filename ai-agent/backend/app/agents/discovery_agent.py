"""Job Discovery Agent (Agent 1)."""

import asyncio
import hashlib
import logging
import re
import unicodedata
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.base import JobListing, JobPortalConnector, JobSearchQuery
from app.connectors.registry import PortalConnectorRegistry
from app.core.exceptions import PortalConnectorError
from app.db.models.job import Job
from app.db.models.job_profile import JobProfile

logger = logging.getLogger(__name__)

class JobDiscoveryAgent:
    """
    Agent 1: Job Discovery Agent.
    Executes concurrent searches across registered portals, deduplicates listings,
    and stores new postings into the database.
    """

    MAX_CONCURRENT_SEARCHES = 5

    @classmethod
    def _normalize(cls, value: str) -> str:
        normalized = unicodedata.normalize("NFKC", value).casefold()
        return re.sub(r"[\W_]+", "", normalized)

    @classmethod
    def compute_canonical_hash(
        cls,
        title: str,
        company: str,
        url: str = "",
        location: str = ""
    ) -> str:
        """Computes a deterministic hash to identify duplicate postings across portals."""
        norm_title = cls._normalize(title)
        norm_company = cls._normalize(company)
        norm_location = cls._normalize(location)
        identity = f"{norm_title}:{norm_company}:{norm_location}"
        if not norm_title or not norm_company:
            identity = f"{identity}:{url.strip().rstrip('/').casefold()}"
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()

    @classmethod
    async def _search_connector(
        cls,
        connector: JobPortalConnector,
        search_query: JobSearchQuery,
        semaphore: asyncio.Semaphore
    ) -> List[JobListing]:
        async with semaphore:
            return await connector.search_jobs(search_query)

    @classmethod
    async def discover_jobs(
        cls,
        job_profile: JobProfile,
        db: AsyncSession,
        limit_per_portal: int = 15
    ) -> List[Job]:
        """
        Executes multi-portal search based on a candidate's targeted JobProfile.
        Returns newly discovered and stored Job models.
        """
        search_query = JobSearchQuery(
            role_titles=job_profile.target_job_titles,
            skills=job_profile.target_skills,
            locations=job_profile.preferred_locations,
            remote=job_profile.remote_preference.upper() == "REMOTE",
            experience_years_min=job_profile.min_years_experience,
            limit=limit_per_portal
        )

        PortalConnectorRegistry.initialize()
        connectors = PortalConnectorRegistry.get_search_connectors()
        if not connectors:
            raise PortalConnectorError("No registered portal connectors support job search.")

        semaphore = asyncio.Semaphore(cls.MAX_CONCURRENT_SEARCHES)
        tasks = [cls._search_connector(conn, search_query, semaphore) for conn in connectors]
        search_results = await asyncio.gather(*tasks, return_exceptions=True)

        flattened_listings: List[JobListing] = []
        successful_searches = 0
        for connector, result in zip(connectors, search_results):
            if isinstance(result, asyncio.CancelledError):
                raise result
            if isinstance(result, BaseException):
                if not isinstance(result, Exception):
                    raise result
                logger.warning(
                    "Job search failed for portal '%s': %s",
                    connector.portal_id,
                    result,
                    exc_info=(type(result), result, result.__traceback__)
                )
            elif isinstance(result, list):
                successful_searches += 1
                flattened_listings.extend(result)
            else:
                error = TypeError(
                    f"Connector '{connector.portal_id}' returned a non-list search result."
                )
                logger.warning(
                    "Job search failed for portal '%s': %s",
                    connector.portal_id,
                    error,
                    exc_info=(type(error), error, error.__traceback__)
                )

        if not successful_searches:
            raise PortalConnectorError(
                f"Job search failed for all {len(connectors)} search-capable portal connectors."
            )

        # Deduplicate within the current batch using normalized posting identity.
        unique_listings: Dict[str, JobListing] = {}
        for listing in flattened_listings:
            h = cls.compute_canonical_hash(
                listing.title,
                listing.company_name,
                listing.url,
                listing.location or ""
            )
            if h not in unique_listings:
                unique_listings[h] = listing

        # Compare against stored postings as well so repeat searches across portals
        # do not create duplicates without requiring a schema migration.
        existing_result = await db.execute(
            select(Job.title, Job.company_name, Job.url, Job.location)
        )
        existing_keys: set[str] = set()
        existing_urls: set[str] = set()
        for title, company, url, location in existing_result.all():
            existing_keys.add(cls.compute_canonical_hash(title, company, url, location or ""))
            existing_urls.add(url.rstrip("/").casefold())

        persisted_jobs: List[Job] = []
        for listing in unique_listings.values():
            canonical_hash = cls.compute_canonical_hash(
                listing.title,
                listing.company_name,
                listing.url,
                listing.location or ""
            )
            normalized_url = listing.url.rstrip("/").casefold()
            if canonical_hash in existing_keys or normalized_url in existing_urls:
                continue

            job_record = Job(
                portal_id=listing.portal_id,
                external_job_id=listing.external_job_id,
                url=listing.url,
                title=listing.title,
                company_name=listing.company_name,
                location=listing.location,
                employment_type=listing.employment_type or "FULL_TIME",
                salary_range=listing.salary_range,
                posted_date=listing.posted_date,
                status="DISCOVERED"
            )
            db.add(job_record)
            persisted_jobs.append(job_record)
            existing_keys.add(canonical_hash)
            existing_urls.add(normalized_url)

        if persisted_jobs:
            await db.commit()
            for j in persisted_jobs:
                await db.refresh(j)

        return persisted_jobs
