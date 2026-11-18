"""Resume optimization with strict master-fact grounding."""

import re
from copy import deepcopy
from typing import Any

from pydantic import BaseModel, Field

from app.core.exceptions import HallucinationDetectedError


class GroundingIssue(BaseModel):
    category: str
    value: str


class GroundingReport(BaseModel):
    verified: bool
    issues: list[GroundingIssue] = Field(default_factory=list)
    rejected_claims: list[str] = Field(default_factory=list)


class ResumeOptimizationResult(BaseModel):
    tailored_text: str
    tailored_json: dict[str, Any]
    ats_score: float
    grounding_report: GroundingReport


class ResumeOptimizerAgent:
    """Tailors resume structure using only verified candidate facts."""

    @staticmethod
    def _normalize(value: str) -> str:
        return re.sub(r"[\W_]+", "", value.casefold())

    @classmethod
    def _dedupe(cls, values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            clean = " ".join(str(value).split())
            key = cls._normalize(clean)
            if clean and key not in seen:
                seen.add(clean)
                result.append(clean)
                seen.add(key)
        return result

    @classmethod
    def collect_ground_facts(
        cls,
        candidate_profile: Any,
        resume: Any
    ) -> dict[str, Any]:
        """Collects the authoritative facts used to accept or reject tailoring."""
        skills = list(getattr(candidate_profile, "verified_skills", []) or [])
        experience: list[dict[str, Any]] = []
        education: list[dict[str, Any]] = []
        projects: list[dict[str, Any]] = []
        text_fragments: list[str] = []

        for item in getattr(candidate_profile, "verified_experience", []) or []:
            clean = deepcopy(dict(item))
            experience.append(clean)
            text_fragments.append(" ".join(str(v) for v in clean.values()))
            for technology in clean.get("technologies", []) or []:
                skills.append(str(technology))
            for bullet in clean.get("bullet_points", []) or []:
                text_fragments.append(str(bullet))

        for item in getattr(candidate_profile, "verified_education", []) or []:
            clean = deepcopy(dict(item))
            education.append(clean)
            text_fragments.append(" ".join(str(v) for v in clean.values()))

        for item in getattr(candidate_profile, "learning_and_projects", []) or []:
            clean = deepcopy(dict(item))
            projects.append(clean)
            text_fragments.append(" ".join(str(v) for v in clean.values()))
            for technology in clean.get("technologies", []) or []:
                skills.append(str(technology))

        parsed = deepcopy(getattr(resume, "parsed_json", {}) or {})
        parsed_skills = parsed.get("skills", []) or []
        if isinstance(parsed_skills, list):
            if not skills:
                skills.extend(str(skill) for skill in parsed_skills)

        if not experience:
            for item in parsed.get("experience", []) or []:
                if isinstance(item, dict):
                    clean = deepcopy(item)
                    experience.append(clean)
                    text_fragments.append(" ".join(str(v) for v in clean.values()))

        if not education:
            for item in parsed.get("education", []) or []:
                if isinstance(item, dict):
                    clean = deepcopy(item)
                    education.append(clean)
                    text_fragments.append(" ".join(str(v) for v in clean.values()))

        if not projects:
            for item in parsed.get("projects", []) or []:
                if isinstance(item, dict):
                    clean = deepcopy(item)
                    projects.append(clean)
                    text_fragments.append(" ".join(str(v) for v in clean.values()))

        # Raw parsed resume text is not independent ground truth. Candidate
        # verified facts remain primary; parsed experience is added only below
        # when no verified experience exists.
        text_fragments.extend(
            str(value)
            for value in [
                getattr(candidate_profile, "first_name", ""),
                getattr(candidate_profile, "last_name", ""),
                getattr(candidate_profile, "email", ""),
                getattr(candidate_profile, "phone", ""),
                getattr(candidate_profile, "location_city", ""),
                getattr(candidate_profile, "location_country", ""),
            ]
            if value
        )

        return {
            "skills": cls._dedupe(skills),
            "experience": experience,
            "education": education,
            "projects": projects,
            "text": "\n".join(text_fragments)
        }

    @classmethod
    def _contains_ground_fact(cls, claim: str, ground_facts: dict[str, Any]) -> bool:
        claim_key = cls._normalize(claim)
        if not claim_key:
            return True
        for fact in ground_facts["skills"]:
            if cls._normalize(str(fact)) == claim_key:
                return True
        for fragment in ground_facts["text"].splitlines():
            if claim_key in cls._normalize(fragment):
                return True
        return False

    @classmethod
    def verify_grounding(
        cls,
        tailored_json: dict[str, Any],
        ground_facts: dict[str, Any]
    ) -> GroundingReport:
        """Rejects unsupported skills, experience, credentials, and invented metrics."""
        issues: list[GroundingIssue] = []
        rejected_claims: list[str] = []

        skills = tailored_json.get("skills", []) or []
        if not isinstance(skills, list):
            return GroundingReport(
                verified=False,
                issues=[GroundingIssue(category="skills", value="Skills must be a list.")],
                rejected_claims=["skills"]
            )

        allowed_skill_keys = {
            cls._normalize(str(skill))
            for skill in ground_facts["skills"]
        }
        for skill in skills:
            if cls._normalize(str(skill)) not in allowed_skill_keys:
                issue = GroundingIssue(category="skill", value=str(skill))
                issues.append(issue)
                rejected_claims.append(str(skill))

        for experience in tailored_json.get("experience", []) or []:
            if not isinstance(experience, dict):
                issue = GroundingIssue(category="experience", value=str(experience))
                issues.append(issue)
                rejected_claims.append(str(experience))
                continue
            for header_value in (
                experience.get("title"),
                experience.get("company"),
                experience.get("start_date"),
                experience.get("end_date"),
            ):
                if header_value and not cls._contains_ground_fact(
                    str(header_value),
                    ground_facts
                ):
                    issue = GroundingIssue(
                        category="experience_header",
                        value=str(header_value)
                    )
                    issues.append(issue)
                    rejected_claims.append(str(header_value))
            bullets = experience.get("bullet_points") or experience.get("bullets") or []
            for bullet in bullets:
                if not cls._contains_ground_fact(str(bullet), ground_facts):
                    issue = GroundingIssue(category="experience_bullet", value=str(bullet))
                    issues.append(issue)
                    rejected_claims.append(str(bullet))

        for education in tailored_json.get("education", []) or []:
            if not isinstance(education, dict):
                continue
            serialized = " ".join(str(value) for value in education.values() if value)
            if not cls._contains_ground_fact(serialized, ground_facts):
                issue = GroundingIssue(category="education", value=serialized)
                issues.append(issue)
                rejected_claims.append(serialized)

        for project in tailored_json.get("projects", []) or []:
            if not isinstance(project, dict):
                continue
            serialized = " ".join(str(value) for value in project.values() if value)
            if not cls._contains_ground_fact(serialized, ground_facts):
                issue = GroundingIssue(category="project", value=serialized)
                issues.append(issue)
                rejected_claims.append(serialized)

        ground_numbers = set(
            re.findall(r"\b\d+(?:[.,]\d+)?%|\b\d+(?:[.,]\d+)*\b", ground_facts["text"])
        )
        text_to_check = " ".join([
            str(tailored_json.get("summary", "")),
            " ".join(str(skill) for skill in skills),
            " ".join(
                str(bullet)
                for experience in tailored_json.get("experience", []) or []
                if isinstance(experience, dict)
                for bullet in (
                    experience.get("bullet_points")
                    or experience.get("bullets")
                    or []
                )
            )
        ])
        for number in re.findall(r"\b\d+(?:[.,]\d+)?%|\b\d+(?:[.,]\d+)*\b", text_to_check):
            if number not in ground_numbers:
                issue = GroundingIssue(category="invented_metric", value=number)
                issues.append(issue)
                rejected_claims.append(number)

        return GroundingReport(
            verified=not issues,
            issues=issues,
            rejected_claims=cls._dedupe(rejected_claims)
        )

    @classmethod
    def _tailor_experience(
        cls,
        ground_facts: dict[str, Any]
    ) -> list[dict[str, Any]]:
        tailored: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in ground_facts["experience"]:
            clean = deepcopy(item)
            if "bullets" in clean and "bullet_points" not in clean:
                clean["bullet_points"] = clean.pop("bullets")
            serialized = (
                f"{clean.get('title', '')}|{clean.get('company', '')}|"
                f"{clean.get('start_date', '')}|{clean.get('end_date', '')}"
            )
            key = cls._normalize(serialized)
            if key not in seen:
                seen.add(key)
                tailored.append(clean)
        return tailored

    @classmethod
    def optimize(
        cls,
        candidate_profile: Any,
        resume: Any,
        job: Any,
        description: Any
    ) -> ResumeOptimizationResult:
        ground_facts = cls.collect_ground_facts(candidate_profile, resume)
        parsed = deepcopy(resume.parsed_json or {})
        contact = deepcopy(parsed.get("contact_info") or {})
        full_name = (
            f"{candidate_profile.first_name} {candidate_profile.last_name}".strip()
        )
        contact.setdefault("name", full_name)
        contact.setdefault("email", candidate_profile.email)
        if candidate_profile.phone:
            contact.setdefault("phone", candidate_profile.phone)
        if candidate_profile.location_city or candidate_profile.location_country:
            contact.setdefault(
                "location",
                ", ".join(filter(None, [
                    candidate_profile.location_city,
                    candidate_profile.location_country
                ]))
            )
        if candidate_profile.linkedin_url:
            contact.setdefault("linkedin_url", candidate_profile.linkedin_url)
        if candidate_profile.github_url:
            contact.setdefault("github_url", candidate_profile.github_url)

        mandatory = (
            list(description.extracted_mandatory_skills)
            if getattr(description, "extracted_mandatory_skills", None)
            else []
        )
        optional = (
            list(description.extracted_optional_skills)
            if getattr(description, "extracted_optional_skills", None)
            else []
        )

        allowed_skills = ground_facts["skills"]
        allowed_keys = {cls._normalize(skill) for skill in allowed_skills}
        tailored_skills: list[str] = []
        for skill in mandatory + optional:
            if cls._normalize(str(skill)) in allowed_keys:
                tailored_skills.append(str(skill))
        for skill in allowed_skills:
            if cls._normalize(skill) not in {cls._normalize(item) for item in tailored_skills}:
                tailored_skills.append(skill)

        summary_skills = tailored_skills[:6]
        if summary_skills:
            summary = (
                "Professional profile with verified expertise in "
                + ", ".join(summary_skills[:-1])
                + ((" and " + summary_skills[-1]) if len(summary_skills) > 1 else summary_skills[0])
                + "."
            )
        else:
            summary = "Professional profile based on verified career history."

        tailored_json = {
            "full_name": contact.get("name"),
            "contact_info": contact,
            "summary": summary,
            "skills": cls._dedupe(tailored_skills),
            "experience": cls._tailor_experience(ground_facts),
            "education": ground_facts["education"],
            "projects": ground_facts["projects"],
        }

        grounding_report = cls.verify_grounding(tailored_json, ground_facts)
        if not grounding_report.verified:
            raise HallucinationDetectedError(
                "Resume optimization was rejected because unsupported claims were detected.",
                {
                    "issues": [issue.model_dump() for issue in grounding_report.issues],
                    "rejected_claims": grounding_report.rejected_claims
                }
            )

        if mandatory:
            mandatory_matched = sum(
                1
                for skill in mandatory
                if cls._normalize(str(skill)) in {
                    cls._normalize(item) for item in tailored_json["skills"]
                }
            )
            mandatory_score = mandatory_matched / len(mandatory)
        else:
            mandatory_score = 1.0

        if optional:
            optional_matched = sum(
                1
                for skill in optional
                if cls._normalize(str(skill)) in {
                    cls._normalize(item) for item in tailored_json["skills"]
                }
            )
            optional_score = optional_matched / len(optional)
        else:
            optional_score = 1.0

        ats_score = round((mandatory_score * 0.70 + optional_score * 0.30) * 100, 2)
        tailored_text = cls._render_tailored_text(tailored_json)
        return ResumeOptimizationResult(
            tailored_text=tailored_text,
            tailored_json=tailored_json,
            ats_score=ats_score,
            grounding_report=grounding_report
        )

    @classmethod
    def _render_tailored_text(cls, tailored_json: dict[str, Any]) -> str:
        lines = [str(tailored_json.get("full_name", ""))]
        if tailored_json.get("summary"):
            lines.extend(["", "Professional Summary", tailored_json["summary"]])
        if tailored_json.get("skills"):
            lines.extend(["", "Skills", ", ".join(tailored_json["skills"])])
        if tailored_json.get("experience"):
            lines.append("")
            lines.append("Professional Experience")
            for item in tailored_json["experience"]:
                header = " | ".join(
                    str(value)
                    for value in [
                        item.get("title"),
                        item.get("company"),
                        item.get("start_date"),
                        item.get("end_date")
                    ]
                    if value
                )
                lines.append(header)
                for bullet in item.get("bullet_points") or item.get("bullets") or []:
                    lines.append(f"- {bullet}")
        if tailored_json.get("education"):
            lines.extend(["", "Education"])
            for item in tailored_json["education"]:
                lines.append(" | ".join(str(value) for value in item.values() if value))
        if tailored_json.get("projects"):
            lines.extend(["", "Projects"])
            for item in tailored_json["projects"]:
                lines.append(" | ".join(str(value) for value in item.values() if value))
        return "\n".join(lines).strip()
