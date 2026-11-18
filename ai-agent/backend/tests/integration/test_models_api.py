"""Integration Tests for FastAPI Endpoints and Model Settings."""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app

@pytest.mark.asyncio
async def test_root_health_endpoint():
    """Verify root health check endpoint returns 200 and system metadata."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OPERATIONAL"
        assert data["is_local_mode"] is True

@pytest.mark.asyncio
async def test_models_settings_endpoint():
    """Verify /api/v1/models/settings returns active configuration."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/models/settings")
        assert response.status_code == 200
        data = response.json()
        assert data["default_provider"] == "ollama"
        assert data["is_local_mode"] is True
        assert data["allow_cloud_fallback"] is False

@pytest.mark.asyncio
async def test_models_select_endpoint():
    """Verify /api/v1/models/select dynamically updates active model."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/models/select",
            json={"model_name": "qwen2.5:7b-instruct", "embedding_model_name": "nomic-embed-text"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "UPDATED"
        assert data["active_model"] == "qwen2.5:7b-instruct"
        assert data["active_embedding_model"] == "nomic-embed-text"

@pytest.mark.asyncio
async def test_models_health_endpoint():
    """Verify /api/v1/models/health reports status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/models/health")
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "ollama"
        assert data["is_local"] is True
