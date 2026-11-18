"""Unit tests for strict resume optimization."""

from types import SimpleNamespace

from app.agents.resume_optimizer_agent import ResumeOptimizerAgent


def _candidate():
    return SimpleNamespace(
        first_name="Alex",
        last_name="Engineer",
        email="alex@example.com",
        phone="+1-555-0100",
        location_city="Seattle",
        location_country="USA",
        linkedin_url="https://linkedin.com/in/alex",
        github_url="https://github.com/alex",
        verified_skills=["Python", "FastAPI", "PostgreSQL"],
        verified_experience=[
            {
                "title": "Backend Engineer",
                "company": "Example Systems",
                "start_date": "2021-01",
                "end_date": "Present",
                "bullet_points": [
                    "Built API services with Python and FastAPI.",
                    "Reduced latency by 30% using PostgreSQL indexing."
                ],
                "technologies": ["Python", "FastAPI", "PostgreSQL"]
            }
        ],
        verified_education=[
            {
                "institution": "Example University",
                "degree": "B.S. Computer Science",
                "graduation_year": 2020
            }
        ],
        learning_and_projects=[
            {
                "title": "Open API Project",
                "description": "Built a REST API",
                "technologies": ["Python", "FastAPI"],
                "is_commercial": False
            }
        ]
    )


def _resume():
    return SimpleNamespace(
        parsed_json={
            "contact_info": {"name": "Alex Engineer"},
            "summary": "Backend engineer",
            "skills": ["Python", "FastAPI", "PostgreSQL"],
            "experience": [
                {
                    "title": "Backend Engineer",
                    "company": "Example Systems",
                    "start_date": "2021-01",
                    "end_date": "Present",
                    "bullet_points": [
                        "Built API services with Python and FastAPI.",
                        "Reduced latency by 30% using PostgreSQL indexing."
                    ]
                }
            ],
            "education": [],
            "projects": []
        },
        raw_text="Alex Engineer\nBuilt API services with Python and FastAPI."
    )


def _description():
    return SimpleNamespace(
        extracted_mandatory_skills=["Python", "FastAPI", "Kubernetes"],
        extracted_optional_skills=["PostgreSQL"]
    )


def test_optimizer_reorders_only_verified_skills_and_scores_ats_coverage():
    candidate = _candidate()
    resume = _resume()
    description = _description()

    result = ResumeOptimizerAgent.optimize(
        candidate_profile=candidate,
        resume=resume,
        job=SimpleNamespace(title="Backend Engineer", company_name="Target Co"),
        description=description
    )

    assert "Kubernetes" not in result.tailored_json["skills"]
    assert "Python" in result.tailored_json["skills"]
    assert "FastAPI" in result.tailored_json["skills"]
    assert result.grounding_report.verified is True
    assert result.ats_score == 76.67


def test_verifier_rejects_unsupported_skill():
    candidate = _candidate()
    ground_facts = ResumeOptimizerAgent.collect_ground_facts(candidate, _resume())
    tailored = {
        "summary": "Experienced engineer",
        "skills": ["Python", "Kubernetes"],
        "experience": [],
        "education": [],
        "projects": []
    }

    report = ResumeOptimizerAgent.verify_grounding(tailored, ground_facts)

    assert report.verified is False
    assert "Kubernetes" in report.rejected_claims


def test_verifier_rejects_metric_not_present_in_master_facts():
    ground_facts = ResumeOptimizerAgent.collect_ground_facts(_candidate(), _resume())
    tailored = {
        "summary": "Improved throughput",
        "skills": ["Python"],
        "experience": [
            {
                "title": "Backend Engineer",
                "company": "Example Systems",
                "bullet_points": ["Reduced transaction failures by 95%."]
            }
        ],
        "education": [],
        "projects": []
    }

    report = ResumeOptimizerAgent.verify_grounding(tailored, ground_facts)

    assert report.verified is False
    assert "95%" in report.rejected_claims


def test_optimizer_does_not_copy_unverified_bullet_from_parsed_resume():
    candidate = _candidate()
    resume = _resume()
    resume.parsed_json["experience"][0]["bullet_points"].append(
        "Built a quantum trading engine with 99.99% uptime."
    )

    result = ResumeOptimizerAgent.optimize(
        candidate_profile=candidate,
        resume=resume,
        job=SimpleNamespace(title="Backend Engineer", company_name="Target Co"),
        description=_description()
    )

    all_bullets = [
        bullet
        for experience in result.tailored_json["experience"]
        for bullet in experience.get("bullet_points", [])
    ]
    assert "Built a quantum trading engine with 99.99% uptime." not in all_bullets
