"""Unit Tests for Ollama Provider, Cloud Guardrails, and Factory."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.config import settings
from app.ai.providers.ollama_provider import OllamaProvider
from app.ai.providers.cloud_providers import OpenAIProvider
from app.ai.providers.factory import LLMProviderFactory
from app.core.exceptions import OllamaUnavailableError, ModelNotFoundError, ApprovalRequiredError

@pytest.mark.asyncio
async def test_ollama_health_check_offline():
    """Verify that when Ollama is offline, a clear actionable error is returned without crashing."""
    provider = OllamaProvider(base_url="http://127.0.0.1:99999")
    health = await provider.health_check()
    assert health["is_healthy"] is False
    assert "Unable to connect to Ollama" in health["error_message"]
    assert health["is_local"] is True

@pytest.mark.asyncio
async def test_ollama_health_check_online_with_model():
    """Verify health check logic when Ollama responds with model list."""
    provider = OllamaProvider(model_name="qwen2.5:7b-instruct")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "models": [{"name": "qwen2.5:7b-instruct:latest", "size": 4500000000}]
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        health = await provider.health_check()
        assert health["is_healthy"] is True
        assert "qwen2.5:7b-instruct:latest" in health["installed_models"]
        assert health["latency_ms"] is not None

@pytest.mark.asyncio
async def test_cloud_provider_strict_guardrail_blocks_silent_fallback():
    """Verify that cloud providers reject inference calls when cloud fallback is not consented."""
    cloud_provider = OpenAIProvider()
    with pytest.raises(ApprovalRequiredError) as exc_info:
        await cloud_provider.generate(prompt="Hello")
    assert "Cloud LLM inference via 'openai' is currently blocked" in str(exc_info.value)

@pytest.mark.asyncio
async def test_provider_factory_resolution():
    """Verify that provider factory yields correct singleton and manages model selection."""
    provider = LLMProviderFactory.get_provider("ollama")
    assert isinstance(provider, OllamaProvider)

    # Test dynamic model selection
    LLMProviderFactory.set_active_model("llama3.2:3b")
    assert LLMProviderFactory.get_active_model_name() == "llama3.2:3b"

    LLMProviderFactory.set_active_embedding_model("bge-small-en-v1.5")
    assert LLMProviderFactory.get_active_embedding_model_name() == "bge-small-en-v1.5"
