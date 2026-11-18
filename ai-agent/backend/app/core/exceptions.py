"""Application custom typed exceptions."""

from typing import Optional, Dict, Any

class JobAgentException(Exception):
    """Base exception for all application errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

# AI & LLM Exceptions
class AIProviderError(JobAgentException):
    """Raised when an AI provider fails or encounters an unrecoverable error."""
    pass

class OllamaUnavailableError(AIProviderError):
    """Raised when local Ollama service is offline or unreachable."""
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        message: Optional[str] = None
    ):
        msg = message or (
            f"Ollama local service is not reachable at '{base_url}'. "
            "Please ensure Ollama is installed and running (e.g. run 'ollama serve'). "
            "The system is configured in Local-First mode and will NEVER silently "
            "switch to external cloud services without your explicit consent."
        )
        super().__init__(msg, {"base_url": base_url, "provider": "ollama"})

class ModelNotFoundError(AIProviderError):
    """Raised when the specified model has not been downloaded in Ollama."""
    def __init__(self, model_name: str):
        super().__init__(
            f"Model '{model_name}' is not installed locally. "
            f"Run 'ollama pull {model_name}' to download it.",
            {"model_name": model_name}
        )

class HallucinationDetectedError(JobAgentException):
    """Raised when generated resume content violates candidate ground truth."""
    pass

class PromptInjectionDetectedError(JobAgentException):
    """Raised when an untrusted input attempts prompt injection."""
    pass

# Human-In-The-Loop Approval Exceptions
class ApprovalRequiredError(JobAgentException):
    """Raised when an action requires human approval before proceeding."""
    pass

class InvalidApprovalTokenError(JobAgentException):
    """Raised when an approval token is expired, invalid, or already consumed."""
    pass

# Portal & Automation Exceptions
class PortalConnectorError(JobAgentException):
    """Base error for portal connector failures."""
    pass

class AntiBotChallengeDetectedError(PortalConnectorError):
    """Raised when Cloudflare Turnstile, reCAPTCHA, or Akamai blocks automation."""
    pass

class FormFieldNotFoundError(PortalConnectorError):
    """Raised when an expected form field cannot be found in the DOM."""
    pass
