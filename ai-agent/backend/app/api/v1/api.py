"""API v1 Aggregator Router."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    applications,
    candidates,
    job_profiles,
    jobs,
    models,
    portals,
    resumes,
    vault,
    workflows,
)

api_router = APIRouter()
api_router.include_router(models.router)
api_router.include_router(candidates.router)
api_router.include_router(job_profiles.router)
api_router.include_router(vault.router)
api_router.include_router(resumes.router)
api_router.include_router(portals.router)
api_router.include_router(jobs.router)
api_router.include_router(workflows.router)
api_router.include_router(applications.router)
