"""Unit Tests for JD Analysis Agent (Agent 3)."""

from unittest.mock import AsyncMock, patch

import pytest

from app.agents.jd_analysis_agent import JDAnalysisAgent, ParsedJDRequirements
from app.core.exceptions import AIProviderError

SAMPLE_JD = """
Job Title: Senior Staff AI Architect
Location: Remote
Experience: 6+ years

Key Requirements:
- 6+ years designing large-scale distributed systems in Python.
- Deep expertise in FastAPI, PostgreSQL, Docker, and Kubernetes.
- Experience building agentic workflows with LangGraph and local LLMs (Ollama).
- Nice to have: React, TypeScript, PyTorch.

Responsibilities:
- Build universal multi-agent systems and optimize inference latency.
- Mentor junior engineers.
"""

def test_heuristic_extraction_parsing():
    """Verify fallback heuristic extracts core technical skills and experience."""
    parsed = JDAnalysisAgent._heuristic_extraction(SAMPLE_JD)

    assert "Python" in parsed.mandatory_skills or "FastAPI" in parsed.mandatory_skills
    assert parsed.experience_years == 6.0
    assert len(parsed.ats_keywords) >= 3
    assert "React" in parsed.optional_skills
    assert "Python" not in parsed.optional_skills
    assert (
        "Build universal multi-agent systems and optimize inference latency."
        in parsed.responsibilities
    )

def test_heuristic_does_not_invent_experience_or_requirements():
    parsed = JDAnalysisAgent._heuristic_extraction("Join our team and help build great products.")

    assert parsed.experience_years == 0.0
    assert parsed.mandatory_skills == []
    assert parsed.optional_skills == []
    assert parsed.responsibilities == []
    assert parsed.ats_keywords == []
    assert parsed.interview_topics == []

def test_compatibility_is_zero_when_jd_has_no_scoring_requirements():
    evaluation = JDAnalysisAgent.calculate_compatibility(
        candidate_skills=["Python"],
        candidate_exp_years=10,
        jd_requirements=ParsedJDRequirements()
    )

    assert evaluation.overall_score == 0.0

def test_absent_optional_requirements_do_not_inflate_score():
    evaluation = JDAnalysisAgent.calculate_compatibility(
        candidate_skills=[],
        candidate_exp_years=0,
        jd_requirements=ParsedJDRequirements(
            mandatory_skills=["Python"],
            experience_years=4
        )
    )

    assert evaluation.overall_score == 0.0
    assert evaluation.skills_score == 0.0

@pytest.mark.asyncio
async def test_analysis_uses_heuristics_and_logs_provider_failure(caplog):
    provider = AsyncMock()
    provider.generate.side_effect = AIProviderError("offline")

    with patch(
        "app.agents.jd_analysis_agent.LLMProviderFactory.get_provider",
        return_value=provider
    ):
        parsed = await JDAnalysisAgent.analyze_jd_text(SAMPLE_JD)

    assert parsed.experience_years == 6.0
    assert "provider failed" in caplog.text

def test_verified_experience_merges_overlapping_jobs():
    experience = [
        {"start_date": "2020-01", "end_date": "2020-12", "is_current": False},
        {"start_date": "2020-06", "end_date": "2021-05", "is_current": False}
    ]

    assert JDAnalysisAgent.calculate_verified_experience_years(experience) == 1.42

def test_verified_experience_does_not_assume_missing_end_date_is_current():
    experience = [{"start_date": "2020-01", "is_current": False}]

    assert JDAnalysisAgent.calculate_verified_experience_years(experience) == 0.0

def test_compatibility_scoring_perfect_match():
    """A complete skills and experience match gets a high score."""
    requirements = ParsedJDRequirements(
        mandatory_skills=["Python", "FastAPI", "Docker", "PostgreSQL"],
        optional_skills=["React", "Kubernetes"],
        experience_years=5.0,
        responsibilities=["Build backend APIs"],
        ats_keywords=["Python", "API"],
        interview_topics=["System Design"]
    )

    candidate_skills = ["Python", "FastAPI", "Docker", "PostgreSQL", "React", "Kubernetes"]
    candidate_exp = 6.0

    eval_result = JDAnalysisAgent.calculate_compatibility(
        candidate_skills=candidate_skills,
        candidate_exp_years=candidate_exp,
        jd_requirements=requirements
    )

    assert eval_result.overall_score >= 95.0
    assert len(eval_result.missing_skills) == 0
    assert "FastAPI" in eval_result.matching_skills

def test_compatibility_scoring_partial_match():
    """Missing mandatory skills lower the score and are reported."""
    requirements = ParsedJDRequirements(
        mandatory_skills=["Python", "FastAPI", "Kubernetes", "Kafka"],
        optional_skills=["GraphQL"],
        experience_years=5.0,
        responsibilities=["Build backend APIs"],
        ats_keywords=["Kubernetes"],
        interview_topics=["System Design"]
    )

    candidate_skills = ["Python", "FastAPI"]
    candidate_exp = 3.0

    eval_result = JDAnalysisAgent.calculate_compatibility(
        candidate_skills=candidate_skills,
        candidate_exp_years=candidate_exp,
        jd_requirements=requirements
    )

    assert eval_result.overall_score < 70.0
    assert "Kubernetes" in eval_result.missing_skills
    assert "Kafka" in eval_result.missing_skills
    assert "FastAPI" in eval_result.matching_skills
