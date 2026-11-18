"""Application Configuration & Environment Settings."""

from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "Universal AI Job Search and Application Agent"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:5173"

    # Security & Encryption
    SECRET_KEY: str = "dev_secret_key_change_in_production_f7a8b9c0d1e2f3a4b5c6d7e8f9"
    ENCRYPTION_MASTER_KEY: str = (
        "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE="
    )  # Development dummy key
    SESSION_EXPIRE_MINUTES: int = 1440
    ALLOWED_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/db/app.db"
    DB_ECHO: bool = False

    # AI Configuration (Ollama Local Default)
    DEFAULT_LLM_PROVIDER: str = "ollama"  # "ollama", "openai", "gemini", "anthropic"
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b-instruct"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    LLM_TEMPERATURE: float = 0.2
    LLM_CONTEXT_WINDOW: int = 8192
    LLM_TIMEOUT_SECONDS: int = 120

    # Optional Cloud Providers (Strictly disabled by default, requires explicit user consent)
    ALLOW_CLOUD_FALLBACK: bool = False
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # ChromaDB Vector Store
    CHROMA_PERSIST_DIRECTORY: str = "./data/chroma"
    CHROMA_COLLECTION_RESUMES: str = "candidate_resume_chunks"
    CHROMA_COLLECTION_JDS: str = "job_description_chunks"

    # Playwright Browser Automation
    PLAYWRIGHT_HEADLESS: bool = False
    BROWSER_PROFILE_DIR: str = "./data/browser_profiles"
    PLAYWRIGHT_TIMEOUT_MS: int = 30000
    BROWSER_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    )

    # Human-In-The-Loop (HITL) Gatekeeper
    REQUIRE_SUBMISSION_APPROVAL: bool = True
    APPROVAL_TOKEN_EXPIRY_SECONDS: int = 600

    # Local Storage Paths
    DATA_DIR: str = "./data"
    RESUME_STORAGE_DIR: str = "./data/resumes"
    VAULT_STORAGE_DIR: str = "./data/vault"
    MAX_RESUME_UPLOAD_BYTES: int = 10 * 1024 * 1024

    @property
    def is_local_llm(self) -> bool:
        return self.DEFAULT_LLM_PROVIDER.lower() == "ollama"

    def ensure_directories(self) -> None:
        """Ensures all local directories exist for isolation and persistence."""
        for path_str in [
            self.DATA_DIR,
            f"{self.DATA_DIR}/db",
            self.CHROMA_PERSIST_DIRECTORY,
            self.VAULT_STORAGE_DIR,
            self.RESUME_STORAGE_DIR,
            self.BROWSER_PROFILE_DIR
        ]:
            Path(path_str).mkdir(parents=True, exist_ok=True)

settings = Settings()
