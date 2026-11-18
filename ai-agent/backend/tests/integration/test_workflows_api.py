"""API tests for starting and resuming checkpointed workflows."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from langgraph.checkpoint.memory import MemorySaver

from app.agents.jd_analysis_agent import ParsedJDRequirements
from app.agents.job_search_orchestrator import build_workflow_graph
from app.api.v1.endpoints.workflows import get_db
from app.main import app


@pytest.mark.asyncio
async def test_workflow_api_starts_paused_review_and_resumes():
    session_id = uuid4()
    graph = build_workflow_graph(MemorySaver())

    async def override_get_db():
        yield object()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with patch(
            "app.agents.job_search_orchestrator.JDAnalysisAgent.analyze_jd_text",
            new=AsyncMock(return_value=ParsedJDRequirements(mandatory_skills=["Python"]))
        ), patch(
            "app.api.v1.endpoints.workflows.get_workflow_graph",
            new=AsyncMock(return_value=graph)
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                started = await client.post(
                    "/api/v1/workflows/",
                    json={
                        "mode": "analyze",
                        "session_id": str(session_id),
                        "raw_jd_text": "A software engineering role requiring Python expertise.",
                        "require_human_approval": True
                    }
                )
                resumed = await client.post(
                    f"/api/v1/workflows/{session_id}/resume",
                    json={"decision": "approve"}
                )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert started.status_code == 202
    assert started.json()["workflow_status"] == "AWAITING_REVIEW"
    assert started.json()["pending_interrupt"]["type"] == "human_review_required"
    assert resumed.status_code == 200
    assert resumed.json()["state"]["approval_status"] == "APPROVED"
    assert resumed.json()["workflow_status"] == "COMPLETED"
