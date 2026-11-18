"""Optional Cloud LLM Providers (Strictly gated by explicit user consent)."""

from typing import List, Dict, Any, Optional, AsyncIterator

from app.config import settings
from app.ai.providers.base import BaseLLMProvider, LLMResponse, EmbeddingResponse
from app.core.exceptions import AIProviderError, ApprovalRequiredError

class GuardedCloudProvider(BaseLLMProvider):
    """Base class for cloud providers enforcing zero silent fallback."""

    provider_name: str = "cloud"

    def _verify_consent(self) -> None:
        if not settings.ALLOW_CLOUD_FALLBACK:
            raise ApprovalRequiredError(
                f"Cloud LLM inference via '{self.provider_name}' is currently blocked by your privacy settings. "
                "The application operates in Local-First mode to protect candidate data and resumes. "
                "To enable cloud inference, you must explicitly enable 'ALLOW_CLOUD_FALLBACK=True' "
                "in your settings or approve the External Transfer modal."
            )

    async def health_check(self) -> Dict[str, Any]:
        self._verify_consent()
        return {
            "provider": self.provider_name,
            "is_healthy": True,
            "active_model": "cloud-model",
            "active_embedding_model": "cloud-embed",
            "is_local": False
        }

    async def list_models(self) -> List[Dict[str, Any]]:
        self._verify_consent()
        return []

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        self._verify_consent()
        raise NotImplementedError("Configure cloud credentials to use external API.")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        self._verify_consent()
        raise NotImplementedError("Configure cloud credentials to use external API.")

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> AsyncIterator[str]:
        self._verify_consent()
        yield ""

    async def get_embeddings(self, texts: List[str]) -> EmbeddingResponse:
        self._verify_consent()
        return EmbeddingResponse(embeddings=[], model_name="cloud", dimensions=0)


class OpenAIProvider(GuardedCloudProvider):
    provider_name: str = "openai"


class GeminiProvider(GuardedCloudProvider):
    provider_name: str = "gemini"


class AnthropicProvider(GuardedCloudProvider):
    provider_name: str = "anthropic"
