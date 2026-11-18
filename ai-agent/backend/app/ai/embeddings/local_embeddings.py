"""Local Dense Embedding Pipeline."""

from typing import List, Optional
from app.ai.providers.factory import LLMProviderFactory
from app.config import settings

class LocalEmbeddingEngine:
    """Manages dense vector embedding generation using local models."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.OLLAMA_EMBEDDING_MODEL

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embeds a collection of documents."""
        if not texts:
            return []
        provider = LLMProviderFactory.get_provider(
            provider_name="ollama",
            embedding_model=self.model_name
        )
        response = await provider.get_embeddings(texts)
        return response.embeddings

    async def embed_query(self, text: str) -> List[float]:
        """Embeds a single query string for semantic search."""
        results = await self.embed_documents([text])
        return results[0] if results else []
