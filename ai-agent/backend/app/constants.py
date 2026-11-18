"""Application-wide constants, job categories, and capability enums."""

from enum import Enum
from typing import List

class AutomationLevel(str, Enum):
    LEVEL_1_OFFICIAL_API = "LEVEL_1_OFFICIAL_API"
    LEVEL_2_ATS_INTEGRATION = "LEVEL_2_ATS_INTEGRATION"
    LEVEL_3_GENERIC_BROWSER = "LEVEL_3_GENERIC_BROWSER"
    LEVEL_4_MANUAL_ASSIST = "LEVEL_4_MANUAL_ASSIST"

class ApplicationStatus(str, Enum):
    DRAFT = "DRAFT"
    PREPARED = "PREPARED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    SUBMITTED = "SUBMITTED"
    SCREENING = "SCREENING"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"

class RemotePreference(str, Enum):
    REMOTE = "REMOTE"
    HYBRID = "HYBRID"
    ONSITE = "ONSITE"
    ANY = "ANY"

class EmploymentType(str, Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACT = "CONTRACT"
    INTERNSHIP = "INTERNSHIP"

# Universal Job Role Categories supported out-of-the-box
UNIVERSAL_JOB_CATEGORIES: List[str] = [
    "Software Engineering",
    "Backend Development",
    "Frontend Development",
    "Full Stack Development",
    "Python Development",
    "Java Development",
    "DevOps",
    "Cloud Engineering",
    "Data Engineering",
    "Data Science",
    "Machine Learning",
    "AI Engineering",
    "AI Agent Development",
    "QA Automation",
    "Cybersecurity",
    "Business Analyst",
    "Product Management",
    "UI/UX Design",
    "Finance",
    "Sales",
    "Marketing",
    "HR",
    "Operations",
    "Customer Support",
    "Other custom roles",
]

# Supported initial portals and ATS engines
PREBUILT_PORTAL_IDS: List[str] = [
    "linkedin",
    "naukri",
    "foundit",
    "indeed",
    "timesjobs",
    "wellfound",
    "greenhouse",
    "lever",
    "workday",
    "smartrecruiters",
    "ashby",
    "icims",
    "taleo",
    "generic_careers",
]
