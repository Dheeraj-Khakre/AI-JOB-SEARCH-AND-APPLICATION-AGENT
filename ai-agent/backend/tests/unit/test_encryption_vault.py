"""Unit Tests for AES-256-GCM Vault and Argon2id Security."""

import pytest
from app.core.encryption import AES256GCMVault
from app.core.security import get_password_hash, verify_password, generate_approval_token
from app.core.exceptions import JobAgentException

def test_password_hashing_and_verification():
    """Verify that Argon2id hashes passwords securely and verifies correctly."""
    plain = "SuperSecretPassword123!"
    hashed = get_password_hash(plain)
    assert hashed != plain
    assert "$argon2" in hashed
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_approval_token_generation():
    """Verify that generated approval tokens have correct prefix and entropy."""
    token = generate_approval_token()
    assert token.startswith("hitl_")
    assert len(token) > 40

def test_aes_256_gcm_vault_encryption_decryption():
    """Verify AES-256-GCM encryption and decryption round-trip."""
    payload = {
        "portal": "linkedin",
        "li_at_cookie": "AQEDAR...",
        "user_email": "candidate@example.com"
    }

    encrypted = AES256GCMVault.encrypt_data(payload, master_key_str="master_passphrase_test")
    assert "ciphertext_b64" in encrypted
    assert "salt_b64" in encrypted
    assert "nonce_b64" in encrypted
    assert encrypted["algorithm"] == "AES-256-GCM-PBKDF2-SHA256"

    # Decrypt with same key
    decrypted = AES256GCMVault.decrypt_data(encrypted, master_key_str="master_passphrase_test")
    assert decrypted == payload
    assert decrypted["portal"] == "linkedin"

def test_aes_256_gcm_vault_rejects_wrong_key():
    """Verify that decrypting with wrong key raises JobAgentException."""
    payload = {"secret": "confidential_api_token"}
    encrypted = AES256GCMVault.encrypt_data(payload, master_key_str="correct_key")

    with pytest.raises(JobAgentException) as exc_info:
        AES256GCMVault.decrypt_data(encrypted, master_key_str="wrong_key")
    assert "Failed to decrypt credentials" in str(exc_info.value)

def test_aes_256_gcm_vault_detects_tampering():
    """Verify that tampering with ciphertext breaks authentication tag and fails."""
    payload = {"key": "value"}
    encrypted = AES256GCMVault.encrypt_data(payload, master_key_str="key123")

    # Corrupt the ciphertext
    raw_b64 = encrypted["ciphertext_b64"]
    corrupted_b64 = ("A" if raw_b64[0] != "A" else "B") + raw_b64[1:]
    encrypted["ciphertext_b64"] = corrupted_b64

    with pytest.raises(JobAgentException):
        AES256GCMVault.decrypt_data(encrypted, master_key_str="key123")
