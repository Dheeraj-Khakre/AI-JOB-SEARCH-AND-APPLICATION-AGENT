"""Integration Tests for Resume Upload, Parsing, Document Rendering, and Versioning APIs."""

import io
from pathlib import Path

import pytest
from docx import Document
from httpx import ASGITransport, AsyncClient

from app.db.session import init_db
from app.main import app


@pytest.mark.asyncio
async def test_resume_upload_parsing_rendering_and_versioning_flow(tmp_path):
    """Verify complete resume lifecycle: upload DOCX, parse, render ATS PDF/DOCX, and create tailored versions."""
    await init_db()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create a Candidate Profile
        cand_res = await client.post(
            "/api/v1/candidates/",
            json={
                "first_name": "Taylor",
                "last_name": "Architect",
                "email": "taylor.arch@example.com",
                "phone": "+1-555-9876",
                "verified_skills": ["Python", "FastAPI", "Docker"]
                ,
                "verified_experience": [
                    {
                        "title": "Staff Backend Engineer",
                        "company": "Pinnacle Technologies",
                        "start_date": "2021-01",
                        "end_date": "Present",
                        "bullet_points": [
                            "Architected real-time streaming pipeline processing 50K events/second."
                        ],
                        "technologies": ["Python", "FastAPI", "Docker"]
                    }
                ]
            }
        )
        assert cand_res.status_code == 201
        candidate_id = cand_res.json()["id"]

        # 2. Synthesize a clean DOCX resume in memory
        doc = Document()
        doc.add_heading("Taylor Architect", level=1)
        doc.add_paragraph("taylor.arch@example.com | (555) 987-6543 | San Francisco, CA")
        doc.add_heading("PROFESSIONAL SUMMARY", level=2)
        doc.add_paragraph("Senior Python & Cloud Architect specializing in resilient distributed systems.")
        doc.add_heading("TECHNICAL SKILLS", level=2)
        doc.add_paragraph("Python, FastAPI, Docker, Kubernetes, PostgreSQL, AWS, LangChain")
        doc.add_heading("WORK EXPERIENCE", level=2)
        doc.add_paragraph("Pinnacle Technologies | Staff Backend Engineer | 2021-01 - Present")
        bp1 = doc.add_paragraph(style="List Bullet")
        bp1.add_run("Architected real-time streaming pipeline processing 50K events/second.")

        docx_stream = io.BytesIO()
        doc.save(docx_stream)
        docx_bytes = docx_stream.getvalue()

        # 3. Upload Resume via Multipart Form
        files = {
            "file": ("taylor_architect_resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        }
        data = {
            "candidate_profile_id": candidate_id
        }

        upload_res = await client.post("/api/v1/resumes/upload", data=data, files=files)
        assert upload_res.status_code == 201
        uploaded_resume = upload_res.json()
        resume_id = uploaded_resume["id"]
        assert uploaded_resume["file_type"] == "DOCX"
        assert "Taylor Architect" in uploaded_resume["raw_text"]
        assert "FastAPI" in uploaded_resume["parsed_json"]["skills"]

        # 4. Generate ATS PDF from Resume
        gen_pdf_res = await client.post(f"/api/v1/resumes/{resume_id}/generate-pdf")
        assert gen_pdf_res.status_code == 200
        assert gen_pdf_res.json()["format"] == "PDF"
        assert Path(gen_pdf_res.json()["file_path"]).exists()

        # 5. Generate ATS DOCX from Resume
        gen_docx_res = await client.post(f"/api/v1/resumes/{resume_id}/generate-docx")
        assert gen_docx_res.status_code == 200
        assert gen_docx_res.json()["format"] == "DOCX"
        assert Path(gen_docx_res.json()["file_path"]).exists()

        # 6. Download PDF Binary
        dl_res = await client.get(f"/api/v1/resumes/{resume_id}/download/pdf")
        assert dl_res.status_code == 200
        assert dl_res.headers["content-type"] == "application/pdf"
        assert len(dl_res.content) > 500

        # 7. Create Tailored Resume Version
        tailored_payload = {
            "resume_id": resume_id,
            "version_label": "Fintech Corp - Lead Python Architect",
            "tailored_text": "Tailored resume focusing on fintech microservices and high reliability",
            "tailored_json": {
                "full_name": "Taylor Architect",
                "summary": "Fintech-focused Lead Python Architect with deep transaction processing background",
                "skills": ["Python", "FastAPI", "Docker"],
                "experience": [
                    {
                        "title": "Staff Backend Engineer",
                        "company": "Pinnacle Technologies",
                        "start_date": "2021-01",
                        "end_date": "Present",
                        "bullet_points": [
                            "Architected real-time streaming pipeline processing 50K events/second."
                        ]
                    }
                ]
            },
            "ats_score": 94.5,
            "grounding_verified": True
        }
        ver_res = await client.post(
            "/api/v1/resumes/versions/",
            json=tailored_payload
        )
        if ver_res.status_code == 422:
            pytest.fail(f"Grounding verification unexpectedly rejected: {ver_res.json()}")
        assert ver_res.status_code == 201
        version = ver_res.json()
        assert version["ats_score"] == 94.5
        assert version["grounding_verified"] is True
        assert version["pdf_file_path"] is not None

        # 8. List Versions for Resume
        ver_list = await client.get(f"/api/v1/resumes/{resume_id}/versions")
        assert ver_list.status_code == 200
        assert len(ver_list.json()) >= 1
