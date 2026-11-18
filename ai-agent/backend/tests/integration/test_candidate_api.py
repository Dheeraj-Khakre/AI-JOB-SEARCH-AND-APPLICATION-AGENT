"""Integration Tests for Candidate Master Profile, Multiple Job Profiles, and Vault APIs."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.session import init_db

@pytest.mark.asyncio
async def test_candidate_profile_and_multi_job_profile_lifecycle():
    """Verify full end-to-end lifecycle for candidate profile, multiple job profiles, and vault."""
    # Ensure tables exist
    await init_db()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Check Universal Job Categories List
        categories_res = await client.get("/api/v1/job-profiles/categories/list")
        assert categories_res.status_code == 200
        cats = categories_res.json()
        assert "Backend Development" in cats
        assert "AI Engineering" in cats

        # 2. Create Candidate Master Profile
        candidate_payload = {
            "first_name": "Alex",
            "last_name": "Developer",
            "email": "alex.dev@example.com",
            "phone": "+1-555-0199",
            "location_city": "San Francisco",
            "location_country": "USA",
            "linkedin_url": "https://linkedin.com/in/alexdev",
            "github_url": "https://github.com/alexdev",
            "verified_skills": ["Python", "FastAPI", "Docker", "PostgreSQL", "LangChain"],
            "verified_experience": [
                {
                    "company": "CloudTech Solutions",
                    "title": "Senior Python Developer",
                    "start_date": "2020-03",
                    "end_date": "Present",
                    "is_current": True,
                    "bullet_points": ["Designed high-throughput REST APIs with FastAPI"],
                    "technologies": ["Python", "FastAPI"]
                }
            ],
            "verified_education": [
                {
                    "institution": "Tech University",
                    "degree": "B.S. Software Engineering",
                    "field_of_study": "Computer Science",
                    "graduation_year": 2019
                }
            ],
            "learning_and_projects": [
                {
                    "title": "Open Source LLM Agent",
                    "description": "Experimenting with multi-agent orchestration",
                    "technologies": ["LangGraph", "Ollama"],
                    "is_commercial": False
                }
            ]
        }
        res = await client.post("/api/v1/candidates/", json=candidate_payload)
        assert res.status_code == 201
        created_candidate = res.json()
        candidate_id = created_candidate["id"]
        assert created_candidate["first_name"] == "Alex"
        assert len(created_candidate["verified_skills"]) == 5

        # 3. Create Target Profile 1: Backend Developer
        job_prof_1_payload = {
            "candidate_profile_id": candidate_id,
            "profile_name": "Senior Python Backend Engineer",
            "target_job_titles": ["Senior Backend Developer", "Staff Python Architect"],
            "target_skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
            "min_years_experience": 5,
            "preferred_locations": ["San Francisco", "Remote"],
            "remote_preference": "REMOTE",
            "expected_salary_min": 160000,
            "is_default": True
        }
        res_p1 = await client.post("/api/v1/job-profiles/", json=job_prof_1_payload)
        assert res_p1.status_code == 201
        prof_1 = res_p1.json()
        assert prof_1["is_default"] is True
        prof_1_id = prof_1["id"]

        # 4. Create Target Profile 2: AI Engineer
        job_prof_2_payload = {
            "candidate_profile_id": candidate_id,
            "profile_name": "AI Agent Developer",
            "target_job_titles": ["AI Engineer", "Agent Systems Architect"],
            "target_skills": ["LangGraph", "Ollama", "Python", "RAG"],
            "min_years_experience": 3,
            "remote_preference": "HYBRID",
            "is_default": False
        }
        res_p2 = await client.post("/api/v1/job-profiles/", json=job_prof_2_payload)
        assert res_p2.status_code == 201
        prof_2 = res_p2.json()
        assert prof_2["is_default"] is False
        prof_2_id = prof_2["id"]

        # 5. List Profiles for Candidate
        list_res = await client.get(f"/api/v1/job-profiles/candidate/{candidate_id}")
        assert list_res.status_code == 200
        profiles_list = list_res.json()
        assert len(profiles_list) == 2

        # 6. Switch Default Profile to AI Engineer
        set_def_res = await client.post(f"/api/v1/job-profiles/{prof_2_id}/set-default")
        assert set_def_res.status_code == 200
        assert set_def_res.json()["is_default"] is True

        # Verify prof_1 is no longer default
        check_p1 = await client.get(f"/api/v1/job-profiles/{prof_1_id}")
        assert check_p1.json()["is_default"] is False

        # 7. Store Credentials in Encrypted Vault
        vault_payload = {
            "service_name": "linkedin",
            "key_identifier": "session_cookie",
            "secret_payload": {"li_at": "test_li_at_secret_token_12345"}
        }
        store_res = await client.post("/api/v1/vault/store", json=vault_payload)
        assert store_res.status_code == 201
        stored_info = store_res.json()
        assert stored_info["service_name"] == "linkedin"

        # 8. Decrypt & Retrieve Credentials
        ret_payload = {
            "service_name": "linkedin",
            "key_identifier": "session_cookie"
        }
        ret_res = await client.post("/api/v1/vault/retrieve", json=ret_payload)
        assert ret_res.status_code == 200
        retrieved_secret = ret_res.json()
        assert retrieved_secret["li_at"] == "test_li_at_secret_token_12345"

        # 9. List Vault Metadata
        vault_list = await client.get("/api/v1/vault/list")
        assert vault_list.status_code == 200
        assert len(vault_list.json()) >= 1
