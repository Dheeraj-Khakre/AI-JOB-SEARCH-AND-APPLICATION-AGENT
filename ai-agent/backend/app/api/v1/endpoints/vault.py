"""Encrypted Credentials Vault Endpoints."""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models.vault import EncryptedCredentialsMetadata
from app.api.v1.endpoints.candidates import get_or_create_default_user
from app.schemas.vault import (
    StoreCredentialsRequest,
    StoredSecretInfo,
    DecryptCredentialsRequest
)
from app.core.encryption import AES256GCMVault

router = APIRouter(prefix="/vault", tags=["Encrypted Credentials Vault"])

@router.post("/store", response_model=StoredSecretInfo, status_code=status.HTTP_201_CREATED)
async def store_secret(
    request: StoreCredentialsRequest,
    db: AsyncSession = Depends(get_db)
):
    """Encrypts sensitive credentials with AES-256-GCM and stores ciphertext metadata."""
    user = await get_or_create_default_user(db)
    user_id = request.user_id or user.id

    # Encrypt payload
    encrypted_bundle = AES256GCMVault.encrypt_data(request.secret_payload)

    # Check if key identifier already exists for this service and user
    result = await db.execute(
        select(EncryptedCredentialsMetadata)
        .where(
            EncryptedCredentialsMetadata.user_id == user_id,
            EncryptedCredentialsMetadata.service_name == request.service_name,
            EncryptedCredentialsMetadata.key_identifier == request.key_identifier
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.ciphertext_b64 = encrypted_bundle["ciphertext_b64"]
        existing.salt_b64 = encrypted_bundle["salt_b64"]
        existing.nonce_b64 = encrypted_bundle["nonce_b64"]
        record = existing
    else:
        record = EncryptedCredentialsMetadata(
            user_id=user_id,
            service_name=request.service_name,
            key_identifier=request.key_identifier,
            ciphertext_b64=encrypted_bundle["ciphertext_b64"],
            salt_b64=encrypted_bundle["salt_b64"],
            nonce_b64=encrypted_bundle["nonce_b64"]
        )
        db.add(record)

    await db.commit()
    await db.refresh(record)
    return record

@router.post("/retrieve", response_model=Dict[str, Any])
async def retrieve_secret(
    request: DecryptCredentialsRequest,
    db: AsyncSession = Depends(get_db)
):
    """Retrieves and decrypts stored credentials for a specific service."""
    user = await get_or_create_default_user(db)
    result = await db.execute(
        select(EncryptedCredentialsMetadata)
        .where(
            EncryptedCredentialsMetadata.user_id == user.id,
            EncryptedCredentialsMetadata.service_name == request.service_name,
            EncryptedCredentialsMetadata.key_identifier == request.key_identifier
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No stored credentials found for service '{request.service_name}' with key '{request.key_identifier}'."
        )

    bundle = {
        "ciphertext_b64": record.ciphertext_b64,
        "salt_b64": record.salt_b64,
        "nonce_b64": record.nonce_b64
    }
    decrypted = AES256GCMVault.decrypt_data(bundle)
    return decrypted

@router.get("/list", response_model=List[StoredSecretInfo])
async def list_stored_secrets(db: AsyncSession = Depends(get_db)):
    """Lists metadata of all stored secrets without exposing decrypted content."""
    user = await get_or_create_default_user(db)
    result = await db.execute(
        select(EncryptedCredentialsMetadata)
        .where(EncryptedCredentialsMetadata.user_id == user.id)
    )
    return result.scalars().all()

@router.delete("/{secret_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_secret(secret_id: str, db: AsyncSession = Depends(get_db)):
    """Permanently deletes an encrypted secret from the vault."""
    record = await db.get(EncryptedCredentialsMetadata, secret_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Secret with ID '{secret_id}' not found."
        )
    await db.delete(record)
    await db.commit()
    return None
