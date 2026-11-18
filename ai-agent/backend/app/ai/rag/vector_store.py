"""ChromaDB Local Vector Store Manager."""

import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.config import settings

class LocalVectorStore:
    """Manages local embedded ChromaDB vector collections."""

    _client: Optional[chromadb.PersistentClient] = None

    @classmethod
    def get_client(cls) -> chromadb.PersistentClient:
        """Initializes or returns singleton persistent ChromaDB client."""
        if cls._client is None:
            persist_dir = Path(settings.CHROMA_PERSIST_DIRECTORY)
            persist_dir.mkdir(parents=True, exist_ok=True)
            cls._client = chromadb.PersistentClient(
                path=str(persist_dir),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
        return cls._client

    @classmethod
    def get_or_create_collection(cls, collection_name: str):
        """Retrieves or creates a named ChromaDB collection."""
        client = cls.get_client()
        return client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )

    @classmethod
    async def add_embeddings(
        cls,
        collection_name: str,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Inserts vectors, raw text, and metadata into a collection."""
        collection = cls.get_or_create_collection(collection_name)
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas or [{} for _ in ids]
        )

    @classmethod
    async def query_similar(
        cls,
        collection_name: str,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Queries for semantically similar chunks."""
        collection = cls.get_or_create_collection(collection_name)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_metadata
        )

        formatted = []
        if results and results.get("ids") and results["ids"][0]:
            count = len(results["ids"][0])
            for i in range(count):
                formatted.append({
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i] if results.get("documents") else "",
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "distance": results["distances"][0][i] if results.get("distances") else 0.0,
                    "similarity": round(1.0 - (results["distances"][0][i] if results.get("distances") else 0.0), 4)
                })
        return formatted
