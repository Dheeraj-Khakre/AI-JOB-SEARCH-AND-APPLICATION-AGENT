"""Unit Tests for ATS Document Generators (PDF & DOCX)."""

import os
from pathlib import Path
from pypdf import PdfReader
from docx import Document

from app.documents.pdf_generator import ATSPdfGenerator
from app.documents.docx_generator import ATSDocxGenerator

SAMPLE_STRUCTURED_DATA = {
    "full_name": "Devin Architect",
    "contact_info": {
        "name": "Devin Architect",
        "email": "devin@example.com",
        "phone": "+1-555-4321",
        "location": "Seattle, WA",
        "linkedin_url": "https://linkedin.com/in/devinarch",
        "github_url": "https://github.com/devinarch"
    },
    "summary": "Accomplished Principal AI Systems Engineer specializing in local-first multi-agent architectures and high-throughput Python backends.",
    "skills": ["Python", "FastAPI", "SQLAlchemy", "LangGraph", "ChromaDB", "Docker", "PostgreSQL"],
    "experience": [
        {
            "title": "Principal Systems Engineer",
            "company": "Apex AI Labs",
            "start_date": "2022-01",
            "end_date": "Present",
            "location": "Remote",
            "bullet_points": [
                "Led engineering of local-first LLM application assistant with 99.9% uptime",
                "Reduced vector retrieval latency to under 30ms using ChromaDB cosine indexing"
            ]
        }
    ],
    "education": [
        {
            "degree": "M.S. Computer Science",
            "field_of_study": "Distributed Systems",
            "institution": "University of Washington",
            "graduation_year": 2021
        }
    ],
    "projects": [
        {
            "title": "Universal Portal Connector",
            "technologies": ["Playwright", "FastAPI"],
            "description": "Engineered automated form prefilling system with human-in-the-loop approval"
        }
    ]
}

def test_ats_pdf_generator(tmp_path):
    """Verify ATS PDF generator outputs valid, readable PDF with selectable text."""
    target_pdf = str(tmp_path / "test_resume.pdf")
    generated_path = ATSPdfGenerator.generate_pdf(SAMPLE_STRUCTURED_DATA, target_pdf)

    assert Path(generated_path).exists()
    assert os.path.getsize(generated_path) > 1000

    # Verify PDF content with pypdf
    reader = PdfReader(generated_path)
    assert len(reader.pages) >= 1
    page_text = reader.pages[0].extract_text()
    assert "Devin Architect" in page_text
    assert "Apex AI Labs" in page_text
    assert "ChromaDB" in page_text

def test_ats_docx_generator(tmp_path):
    """Verify ATS DOCX generator outputs valid Word document with proper headings."""
    target_docx = str(tmp_path / "test_resume.docx")
    generated_path = ATSDocxGenerator.generate_docx(SAMPLE_STRUCTURED_DATA, target_docx)

    assert Path(generated_path).exists()
    assert os.path.getsize(generated_path) > 1000

    # Verify DOCX content with python-docx
    doc = Document(generated_path)
    full_text = "\n".join([p.text for p in doc.paragraphs])
    assert "Devin Architect" in full_text
    assert "Apex AI Labs" in full_text
    assert "Principal Systems Engineer" in full_text
