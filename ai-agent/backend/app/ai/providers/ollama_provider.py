"""Ollama Local LLM Provider Implementation."""

import json
import time
import httpx
from typing import List, Dict, Any, Optional, AsyncIterator

from app.config import settings
from app.ai.providers.base import BaseLLMProvider, LLMResponse, EmbeddingResponse
from app.core.exceptions import OllamaUnavailableError, ModelNotFoundError, AIProviderError

class OllamaProvider(BaseLLMProvider):
    """Local-first LLM provider powered by Ollama."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        embedding_model: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model_name = model_name or settings.OLLAMA_MODEL
        self.embedding_model = embedding_model or settings.OLLAMA_EMBEDDING_MODEL
        self.timeout = timeout_seconds or settings.LLM_TIMEOUT_SECONDS

    def _get_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout, connect=5.0)
        )

    async def health_check(self) -> Dict[str, Any]:
        """Checks connectivity to Ollama and verifies if target models exist."""
        start_time = time.perf_counter()
        try:
            async with self._get_client() as client:
                response = await client.get("/api/tags")
                if response.status_code != 200:
                    return {
                        "is_healthy": False,
                        "error_message": f"Ollama returned HTTP {response.status_code}: {response.text}",
                        "latency_ms": None,
                        "installed_models": []
                    }
                data = response.json()
                models = [m.get("name") for m in data.get("models", [])]
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

                model_installed = any(
                    self.model_name in m or m.startswith(self.model_name)
                    for m in models
                )

                error_msg = None
                if not model_installed:
                    error_msg = (
                        f"Target model '{self.model_name}' is not installed in Ollama. "
                        f"Installed models: {models}. Please run 'ollama pull {self.model_name}'."
                    )

                return {
                    "is_healthy": model_installed,
                    "active_model": self.model_name,
                    "active_embedding_model": self.embedding_model,
                    "latency_ms": latency_ms,
                    "installed_models": models,
                    "error_message": error_msg,
                    "provider": "ollama",
                    "is_local": True
                }
        except httpx.ConnectError:
            return {
                "is_healthy": False,
                "active_model": self.model_name,
                "active_embedding_model": self.embedding_model,
                "latency_ms": None,
                "installed_models": [],
                "error_message": (
                    f"Unable to connect to Ollama at {self.base_url}. "
                    "Please ensure Ollama is installed and running ('ollama serve')."
                ),
                "provider": "ollama",
                "is_local": True
            }
        except Exception as e:
            return {
                "is_healthy": False,
                "active_model": self.model_name,
                "active_embedding_model": self.embedding_model,
                "latency_ms": None,
                "installed_models": [],
                "error_message": f"Ollama error: {str(e)}",
                "provider": "ollama",
                "is_local": True
            }

    async def list_models(self) -> List[Dict[str, Any]]:
        """Lists detailed metadata of all installed local models."""
        try:
            async with self._get_client() as client:
                res = await client.get("/api/tags")
                res.raise_for_status()
                data = res.json()
                results = []
                for m in data.get("models", []):
                    details = m.get("details", {})
                    results.append({
                        "name": m.get("name"),
                        "size_bytes": m.get("size"),
                        "parameter_size": details.get("parameter_size"),
                        "quantization_level": details.get("quantization_level"),
                        "modified_at": m.get("modified_at")
                    })
                return results
        except httpx.ConnectError:
            raise OllamaUnavailableError(self.base_url)
        except Exception as e:
            raise AIProviderError(f"Failed to list Ollama models: {str(e)}")

    async def pull_model(self, model_name: str) -> AsyncIterator[Dict[str, Any]]:
        """Initiates pulling a model and yields status updates."""
        try:
            async with self._get_client() as client:
                async with client.stream(
                    "POST",
                    "/api/pull",
                    json={"name": model_name, "stream": True},
                    timeout=httpx.Timeout(1800.0, connect=10.0)
                ) as response:
                    if response.status_code != 200:
                        raise AIProviderError(f"Failed to pull model: HTTP {response.status_code}")
                    async for line in response.aiter_lines():
                        if line:
                            yield json.loads(line)
        except httpx.ConnectError:
            raise OllamaUnavailableError(self.base_url)

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generates a completion from Ollama."""
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else settings.LLM_TEMPERATURE,
                "num_ctx": settings.LLM_CONTEXT_WINDOW,
            }
        }
        if system_prompt:
            payload["system"] = system_prompt
        if json_schema is not None:
            payload["format"] = "json"

        start_time = time.perf_counter()
        try:
            async with self._get_client() as client:
                res = await client.post("/api/generate", json=payload)
                if res.status_code == 404:
                    raise ModelNotFoundError(self.model_name)
                res.raise_for_status()
                data = res.json()
        except httpx.ConnectError:
            raise OllamaUnavailableError(self.base_url)
        except httpx.TimeoutException:
            raise AIProviderError(f"Ollama request timed out after {self.timeout}s.")
        except Exception as e:
            if isinstance(e, (OllamaUnavailableError, ModelNotFoundError, AIProviderError)):
                raise
            raise AIProviderError(f"Ollama generation failed: {str(e)}")

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response_text = data.get("response", "")

        parsed_json = None
        if json_schema is not None and response_text:
            try:
                parsed_json = json.loads(response_text)
            except json.JSONDecodeError as json_err:
                # Attempt to extract json block if wrapped in markdown
                cleaned = response_text.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                if cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                try:
                    parsed_json = json.loads(cleaned.strip())
                except json.JSONDecodeError:
                    parsed_json = None

        return LLMResponse(
            text=response_text,
            parsed_json=parsed_json,
            model_name=self.model_name,
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count"),
            total_tokens=(data.get("prompt_eval_count", 0) + data.get("eval_count", 0)),
            latency_ms=latency_ms
        )

    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
    ) -> LLMResponse:
        """Executes a chat session with Ollama."""
        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        formatted_messages.extend(messages)

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": formatted_messages,
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else settings.LLM_TEMPERATURE,
                "num_ctx": settings.LLM_CONTEXT_WINDOW,
            }
        }
        if json_schema is not None:
            payload["format"] = "json"

        start_time = time.perf_counter()
        try:
            async with self._get_client() as client:
                res = await client.post("/api/chat", json=payload)
                if res.status_code == 404:
                    raise ModelNotFoundError(self.model_name)
                res.raise_for_status()
                data = res.json()
        except httpx.ConnectError:
            raise OllamaUnavailableError(self.base_url)
        except Exception as e:
            if isinstance(e, (OllamaUnavailableError, ModelNotFoundError)):
                raise
            raise AIProviderError(f"Ollama chat failed: {str(e)}")

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        message_data = data.get("message", {})
        response_text = message_data.get("content", "")

        parsed_json = None
        if json_schema is not None and response_text:
            try:
                parsed_json = json.loads(response_text)
            except json.JSONDecodeError:
                parsed_json = None

        return LLMResponse(
            text=response_text,
            parsed_json=parsed_json,
            model_name=self.model_name,
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count"),
            total_tokens=(data.get("prompt_eval_count", 0) + data.get("eval_count", 0)),
            latency_ms=latency_ms
        )

    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> AsyncIterator[str]:
        """Streams generation chunks asynchronously from Ollama."""
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature if temperature is not None else settings.LLM_TEMPERATURE,
                "num_ctx": settings.LLM_CONTEXT_WINDOW,
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with self._get_client() as client:
                async with client.stream("POST", "/api/generate", json=payload) as response:
                    if response.status_code == 404:
                        raise ModelNotFoundError(self.model_name)
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            chunk = json.loads(line)
                            yield chunk.get("response", "")
        except httpx.ConnectError:
            raise OllamaUnavailableError(self.base_url)

    async def get_embeddings(self, texts: List[str]) -> EmbeddingResponse:
        """Generates dense vector embeddings using Ollama embedding model."""
        embeddings_list = []
        try:
            async with self._get_client() as client:
                for text in texts:
                    res = await client.post(
                        "/api/embeddings",
                        json={"model": self.embedding_model, "prompt": text}
                    )
                    if res.status_code == 404:
                        raise ModelNotFoundError(self.embedding_model)
                    res.raise_for_status()
                    data = res.json()
                    embeddings_list.append(data.get("embedding", []))
        except httpx.ConnectError:
            raise OllamaUnavailableError(self.base_url)
        except Exception as e:
            if isinstance(e, (OllamaUnavailableError, ModelNotFoundError)):
                raise
            raise AIProviderError(f"Ollama embeddings generation failed: {str(e)}")

        dim = len(embeddings_list[0]) if embeddings_list else 0
        return EmbeddingResponse(
            embeddings=embeddings_list,
            model_name=self.embedding_model,
            dimensions=dim
        )
