"""FastAPI Main Application Factory & Gateway."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agents.job_search_orchestrator import close_workflow_graph
from app.api.v1.api import api_router
from app.config import settings
from app.core.exceptions import (
    ApprovalRequiredError,
    HallucinationDetectedError,
    JobAgentException,
    ModelNotFoundError,
    OllamaUnavailableError,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ai_job_agent")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    logger.info("Initializing Universal AI Job Search Agent Backend...")
    # Ensure all local storage directories exist
    settings.ensure_directories()
    logger.info(f"Local storage directories verified at: {settings.DATA_DIR}")
    logger.info(f"Active default LLM Provider: {settings.DEFAULT_LLM_PROVIDER} ({settings.OLLAMA_MODEL})")
    yield
    await close_workflow_graph()
    logger.info("Shutting down Universal AI Job Search Agent Backend...")

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Production-grade, privacy-first Universal AI Job Search and Application Agent. "
        "Operates locally with Ollama, LangGraph multi-agent coordination, and strict Human-in-the-Loop gates."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Restrict CORS to configured local origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# Custom Exception Handlers for clear, actionable responses
@app.exception_handler(OllamaUnavailableError)
async def ollama_unavailable_handler(request: Request, exc: OllamaUnavailableError):
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error_code": "OLLAMA_UNAVAILABLE",
            "message": exc.message,
            "details": exc.details
        }
    )

@app.exception_handler(ModelNotFoundError)
async def model_not_found_handler(request: Request, exc: ModelNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error_code": "MODEL_NOT_FOUND",
            "message": exc.message,
            "details": exc.details
        }
    )

@app.exception_handler(ApprovalRequiredError)
async def approval_required_handler(request: Request, exc: ApprovalRequiredError):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error_code": "APPROVAL_REQUIRED",
            "message": exc.message,
            "details": exc.details
        }
    )

@app.exception_handler(JobAgentException)
async def general_job_agent_handler(request: Request, exc: JobAgentException):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error_code": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details
        }
    )

# Mount API Routers
app.include_router(api_router, prefix="/api/v1")

@app.get("/health", tags=["System Health"])
async def root_health_check():
    """Root heartbeat check for uptime monitoring."""
    return {
        "status": "OPERATIONAL",
        "app_name": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "is_local_mode": settings.is_local_llm,
        "active_llm": settings.OLLAMA_MODEL
    }
