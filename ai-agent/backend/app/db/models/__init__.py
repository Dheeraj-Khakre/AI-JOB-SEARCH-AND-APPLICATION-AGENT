"""SQLAlchemy Database Models Registry."""

from app.db.models.user import User
from app.db.models.candidate import CandidateProfile
from app.db.models.job_profile import JobProfile
from app.db.models.vault import EncryptedCredentialsMetadata
from app.db.models.resume import Resume, ResumeVersion
from app.db.models.portal import PortalRegistry, PortalCapabilities
from app.db.models.job import Job, JobDescription, JobMatch

__all__ = [
    "User",
    "CandidateProfile",
    "JobProfile",
    "EncryptedCredentialsMetadata",
    "Resume",
    "ResumeVersion",
    "PortalRegistry",
    "PortalCapabilities",
    "Job",
    "JobDescription",
    "JobMatch",
]
