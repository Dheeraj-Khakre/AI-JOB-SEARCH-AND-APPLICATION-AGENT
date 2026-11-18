"""Pydantic schemas for AI Model Settings and Health Checks."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class ModelInfo(BaseModel):
    name: str = Field(..., description="Model identifier, e.g. qwen2.5:7b-instruct")
    size_bytes: Optional[int] = Field(None, description="Model size in bytes on disk")
    parameter_size: Optional[str] = Field(None, description="e.g. 7B, 3B")
    quantization_level: Optional[str] = Field(None, description="e.g. Q4_K_M")
    modified_at: Optional[datetime] = None

class ModelHealthStatus(BaseModel):
    provider: str = Field(..., description="Active provider: ollama, openai, gemini, etc.")
    is_healthy: bool = Field(..., description="True if provider is reachable and responsive")
    active_model: str = Field(..., description="Current active LLM model name")
    active_embedding_model: str = Field(..., description="Current active embedding model")
    latency_ms: Optional[float] = Field(None, description="Ping/inference latency in milliseconds")
    installed_models: List[str] = Field(default_factory=list, description="Available local models")
    error_message: Optional[str] = Field(None, description="Detailed actionable error if unhealthy")
    is_local: bool = Field(True, description="True if running completely offline/local")
    checked_at: datetime = Field(default_factory=datetime.utcnow)

class ModelSettingsUpdate(BaseModel):
    provider: Optional[str] = Field(None, description="Target provider (ollama, openai, etc.)")
    model_name: Optional[str] = Field(None, description="Target model name")
    embedding_model_name: Optional[str] = Field(None, description="Target embedding model")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    context_window: Optional[int] = Field(None, ge=1024, le=131072)
    allow_cloud_fallback: Optional[bool] = Field(None, description="Explicit consent for cloud")

class PullModelRequest(BaseModel):
    model_name: str = Field(..., description="Name of the Ollama model to pull, e.g. 'qwen2.5:7b-instruct'")

class PullModelResponse(BaseModel):
    status: str
    message: str
    model_name: str
