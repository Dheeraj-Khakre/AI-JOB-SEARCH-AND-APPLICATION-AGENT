"""Unit Tests for Resume Parsing and Section Extraction."""

import pytest

from app.documents.parser import ResumeSectionExtractor, UnifiedResumeParser

SAMPLE_RESUME_TEXT = """
Sarah Connor
San Francisco, CA | sarah.connor@example.com | (555) 234-5678 | https://linkedin.com/in/sarahconnor | https://github.com/sconnor

PROFESSIONAL SUMMARY
Results-driven Lead Software Engineer with 8+ years of expertise in building distributed backend architectures, Python microservices, and AI workflow automation.

TECHNICAL SKILLS
Languages & Frameworks: Python, FastAPI, Go, TypeScript, React, Docker, Kubernetes, PostgreSQL, Redis, LangChain, Ollama

WORK EXPERIENCE
Cyberdyne Systems | Lead Backend Architect | 2021-03 – Present
• Architected asynchronous message-driven microservices serving 20M requests/day using FastAPI and Redis.
• Reduced database query latency by 45% through connection pooling and index optimization.
• Integrated local LLM inference pipelines using Ollama for automated document classification.

Skynet Defense | Senior Software Engineer | 2017-06 – 2021-02
• Developed REST APIs with Django and PostgreSQL for critical infrastructure telemetry.
• Mentored junior engineers and led code review cycles across 4 squads.

EDUCATION
California Institute of Technology
Bachelor of Science in Computer Science (2017)

PROJECTS
Autonomous Agent Framework
• Built an open-source autonomous agent with LangGraph and local vector embeddings.
"""

def test_resume_section_extractor_contact_info():
    """Verify contact info extraction from resume text."""
    sections = ResumeSectionExtractor.extract_sections(SAMPLE_RESUME_TEXT)
    contact = sections["contact_info"]

    assert contact["email"] == "sarah.connor@example.com"
    assert "linkedin.com/in/sarahconnor" in contact["linkedin_url"]
    assert "github.com/sconnor" in contact["github_url"]
    assert "Sarah Connor" in contact["name"]

def test_resume_section_extractor_sections():
    """Verify section segmentation and skill extraction."""
    sections = ResumeSectionExtractor.extract_sections(SAMPLE_RESUME_TEXT)

    assert "Results-driven Lead Software Engineer" in sections["summary"]
    skills = sections["skills"]
    assert "Python" in skills
    assert "FastAPI" in skills
    assert "Docker" in skills

    exp = sections["experience"]
    assert len(exp) >= 2
    assert any("Cyberdyne" in e["header_line"] for e in exp)
    assert any("Skynet" in e["header_line"] for e in exp)

def test_unsupported_format_raises_exception():
    """Verify unsupported formats raise JobAgentException."""
    with pytest.raises(Exception) as exc_info:
        UnifiedResumeParser.parse_document(b"fake data", "resume.xyz")
    assert "Unsupported file format" in str(exc_info.value)

def test_structured_resume_sections_include_education_projects_and_certifications():
    text = """
Taylor Engineer
taylor@example.com

EDUCATION
Bachelor of Technology in Computer Science
2020

PROJECTS
Payments API
• Built a verified REST API project using Java and Spring Boot.

CERTIFICATIONS
Oracle Java Certification
"""
    sections = ResumeSectionExtractor.extract_sections(text)

    assert sections["education"]
    assert sections["projects"]
    assert sections["certifications"] == [{"name": "Oracle Java Certification"}]

def test_invalid_pdf_signature_is_rejected():
    with pytest.raises(Exception, match="invalid PDF signature"):
        UnifiedResumeParser.parse_document(b"not a pdf", "resume.pdf")

def test_invalid_docx_signature_is_rejected():
    with pytest.raises(Exception, match="valid Office document"):
        UnifiedResumeParser.parse_document(b"not a zip", "resume.docx")
