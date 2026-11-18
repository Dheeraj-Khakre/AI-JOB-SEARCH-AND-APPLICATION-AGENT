"""LLM Provider Factory & Resolution."""

from typing import Dict, Optional
from app.config import settings
from app.ai.providers.base import BaseLLMProvider
from app.ai.providers.ollama_provider import OllamaProvider
from app.ai.providers.cloud_providers import OpenAIProvider, GeminiProvider, AnthropicProvider
from app.core.exceptions import AIProviderError

class LLMProviderFactory:
    """Manages LLM provider instances and active model selection."""

    _instances: Dict[str, BaseLLMProvider] = {}
    _active_provider_name: str = settings.DEFAULT_LLM_PROVIDER.lower()
    _active_model: str = settings.OLLAMA_MODEL
    _active_embedding_model: str = settings.OLLAMA_EMBEDDING_MODEL

    @classmethod
    def get_provider(
        cls,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ) -> BaseLLMProvider:
        """Resolves and returns the configured LLM provider instance."""
        target_provider = (provider_name or cls._active_provider_name).lower()
        target_model = model_name or cls._active_model
        target_embed = embedding_model or cls._active_embedding_model

        cache_key = f"{target_provider}:{target_model}:{target_embed}"

        if cache_key in cls._instances:
            return cls._instances[cache_key]

        if target_provider == "ollama":
            instance = OllamaProvider(
                model_name=target_model,
                embedding_model=target_embed
            )
        elif target_provider == "openai":
            instance = OpenAIProvider()
        elif target_provider == "gemini":
            instance = GeminiProvider()
        elif target_provider == "anthropic":
            instance = AnthropicProvider()
        else:
            raise AIProviderError(f"Unknown LLM provider: '{target_provider}'. Supported: ollama, openai, gemini, anthropic.")

        cls._instances[cache_key] = instance
        return instance

    @classmethod
    def set_active_model(cls, model_name: str) -> None:
        """Dynamically updates the active reasoning model."""
        cls._active_model = model_name

    @classmethod
    def set_active_embedding_model(cls, embedding_model: str) -> None:
        """Dynamically updates the active embedding model."""
        cls._active_embedding_model = embedding_model

    @classmethod
    def set_active_provider(cls, provider_name: str) -> None:
        """Switches the active provider."""
        cls._active_provider_name = provider_name.lower()

    @classmethod
    def get_active_model_name(cls) -> str:
        return cls._active_model

    @classmethod
    def get_active_embedding_model_name(cls) -> str:
        return cls._active_embedding_model

    @classmethod
    def get_active_provider_name(cls) -> str:
        return cls._active_provider_name
