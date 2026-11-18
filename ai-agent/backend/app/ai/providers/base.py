"""Base LLM Provider Interface."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from pydantic import BaseModel, Field

class LLMResponse(BaseModel):
    text: str = Field(..., description="Generated text content")
    parsed_json: Optional[Dict[str, Any]] = Field(None, description="Parsed JSON if requested")
    model_name: str = Field(..., description="Model that produced this output")
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    latency_ms: Optional[float] = None

class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]] = Field(..., description="List of vector embeddings")
    model_name: str
    dimensions: int

class BaseLLMProvider(ABC):
    """Abstract Base Class for all LLM inference providers."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generates text or structured JSON from the model."""
        pass

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        """Executes a multi-turn conversational chat interaction."""
        pass

    @abstractmethod
    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> AsyncIterator[str]:
        """Streams generation chunks asynchronously."""
        pass

    @abstractmethod
    async def get_embeddings(self, texts: List[str]) -> EmbeddingResponse:
        """Computes dense vector embeddings for input texts."""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Verifies connectivity, health, and latency of the provider."""
        pass

    @abstractmethod
    async def list_models(self) -> List[Dict[str, Any]]:
        """Lists all models available under this provider."""
        pass
