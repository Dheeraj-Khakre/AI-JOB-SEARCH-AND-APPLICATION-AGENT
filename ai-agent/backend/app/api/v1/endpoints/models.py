"""AI Model Settings, Health Checks, and Local Model Selector Endpoints."""

from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, status
import logging

from app.config import settings
from app.ai.providers.factory import LLMProviderFactory
from app.ai.providers.ollama_provider import OllamaProvider
from app.schemas.model_settings import (
    ModelHealthStatus,
    ModelInfo,
    ModelSettingsUpdate,
    PullModelRequest,
    PullModelResponse
)
from app.core.exceptions import OllamaUnavailableError, ModelNotFoundError, AIProviderError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/models", tags=["AI Models & Health"])

@router.get("/health", response_model=ModelHealthStatus)
async def check_model_health():
    """Performs a real-time health check on the active LLM provider."""
    provider = LLMProviderFactory.get_provider()
    health_data = await provider.health_check()
    return ModelHealthStatus(
        provider=health_data.get("provider", "ollama"),
        is_healthy=health_data.get("is_healthy", False),
        active_model=LLMProviderFactory.get_active_model_name(),
        active_embedding_model=LLMProviderFactory.get_active_embedding_model_name(),
        latency_ms=health_data.get("latency_ms"),
        installed_models=health_data.get("installed_models", []),
        error_message=health_data.get("error_message"),
        is_local=health_data.get("is_local", True)
    )

@router.get("/ollama/list", response_model=List[ModelInfo])
async def list_local_models():
    """Lists all models currently installed and available in the local Ollama instance."""
    provider = LLMProviderFactory.get_provider("ollama")
    try:
        models = await provider.list_models()
        return [ModelInfo(**m) for m in models]
    except OllamaUnavailableError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=e.message
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query Ollama models: {str(e)}"
        )

@router.post("/ollama/pull", response_model=PullModelResponse)
async def pull_model_endpoint(request: PullModelRequest, background_tasks: BackgroundTasks):
    """Initiates downloading a model into local Ollama."""
    provider = LLMProviderFactory.get_provider("ollama")
    if not isinstance(provider, OllamaProvider):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Active provider is not Ollama"
        )

    # Launch model pull in background task to avoid blocking HTTP worker
    async def _do_pull(name: str):
        try:
            logger.info(f"Starting background pull for Ollama model: {name}")
            async for status_update in provider.pull_model(name):
                logger.debug(f"Pulling {name}: {status_update.get('status')}")
            logger.info(f"Successfully pulled Ollama model: {name}")
        except Exception as err:
            logger.error(f"Error pulling model {name}: {err}")

    background_tasks.add_task(_do_pull, request.model_name)

    return PullModelResponse(
        status="IN_PROGRESS",
        message=f"Model '{request.model_name}' download started in background.",
        model_name=request.model_name
    )

@router.post("/select")
async def select_active_model(update: ModelSettingsUpdate):
    """Updates active reasoning model, embedding model, or provider."""
    if update.model_name:
        LLMProviderFactory.set_active_model(update.model_name)
    if update.embedding_model_name:
        LLMProviderFactory.set_active_embedding_model(update.embedding_model_name)
    if update.provider:
        LLMProviderFactory.set_active_provider(update.provider)

    return {
        "status": "UPDATED",
        "active_provider": LLMProviderFactory.get_active_provider_name(),
        "active_model": LLMProviderFactory.get_active_model_name(),
        "active_embedding_model": LLMProviderFactory.get_active_embedding_model_name()
    }

@router.get("/settings")
async def get_current_model_settings():
    """Returns the current model configuration and privacy status."""
    return {
        "default_provider": settings.DEFAULT_LLM_PROVIDER,
        "active_provider": LLMProviderFactory.get_active_provider_name(),
        "active_model": LLMProviderFactory.get_active_model_name(),
        "active_embedding_model": LLMProviderFactory.get_active_embedding_model_name(),
        "temperature": settings.LLM_TEMPERATURE,
        "context_window": settings.LLM_CONTEXT_WINDOW,
        "timeout_seconds": settings.LLM_TIMEOUT_SECONDS,
        "is_local_mode": LLMProviderFactory.get_active_provider_name() == "ollama",
        "allow_cloud_fallback": settings.ALLOW_CLOUD_FALLBACK
    }
