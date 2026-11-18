"""Encrypted Vault Pydantic Schemas."""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class StoreCredentialsRequest(BaseModel):
    user_id: Optional[str] = None
    service_name: str = Field(..., description="Target portal or service identifier, e.g. 'linkedin', 'greenhouse'")
    key_identifier: str = Field(..., description="Key label, e.g. 'session_token' or 'api_key'")
    secret_payload: Dict[str, Any] = Field(..., description="Arbitrary sensitive credentials dictionary")

class StoredSecretInfo(BaseModel):
    id: str
    service_name: str
    key_identifier: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DecryptCredentialsRequest(BaseModel):
    service_name: str
    key_identifier: str
