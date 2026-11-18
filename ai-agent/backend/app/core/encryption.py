"""AES-256-GCM Cryptographic Vault for Secure Local Secrets Storage."""

import os
import json
import base64
from typing import Dict, Any, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from app.config import settings
from app.core.exceptions import JobAgentException

class AES256GCMVault:
    """Provides authenticated AES-256-GCM symmetric encryption for sensitive portal credentials."""

    @staticmethod
    def derive_key(passphrase: str, salt: bytes) -> bytes:
        """Derives a 256-bit (32-byte) key using PBKDF2 with 600,000 iterations."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=600000,
        )
        return kdf.derive(passphrase.encode("utf-8"))

    @classmethod
    def encrypt_data(
        cls,
        data: Dict[str, Any],
        master_key_str: str = settings.SECRET_KEY
    ) -> Dict[str, str]:
        """
        Encrypts arbitrary dictionary payload into AES-256-GCM ciphertext.
        Returns a dict containing base64-encoded ciphertext, salt, and nonce.
        """
        raw_json = json.dumps(data).encode("utf-8")
        salt = os.urandom(16)
        nonce = os.urandom(12)  # 96-bit nonce for GCM

        derived_key = cls.derive_key(master_key_str, salt)
        aesgcm = AESGCM(derived_key)
        ciphertext = aesgcm.encrypt(nonce, raw_json, None)

        return {
            "ciphertext_b64": base64.b64encode(ciphertext).decode("utf-8"),
            "salt_b64": base64.b64encode(salt).decode("utf-8"),
            "nonce_b64": base64.b64encode(nonce).decode("utf-8"),
            "algorithm": "AES-256-GCM-PBKDF2-SHA256"
        }

    @classmethod
    def decrypt_data(
        cls,
        encrypted_bundle: Dict[str, str],
        master_key_str: str = settings.SECRET_KEY
    ) -> Dict[str, Any]:
        """
        Decrypts and authenticates AES-256-GCM ciphertext.
        Raises JobAgentException if ciphertext has been tampered with or key is incorrect.
        """
        try:
            ciphertext = base64.b64decode(encrypted_bundle["ciphertext_b64"])
            salt = base64.b64decode(encrypted_bundle["salt_b64"])
            nonce = base64.b64decode(encrypted_bundle["nonce_b64"])

            derived_key = cls.derive_key(master_key_str, salt)
            aesgcm = AESGCM(derived_key)
            decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
            return json.loads(decrypted_bytes.decode("utf-8"))
        except Exception as e:
            raise JobAgentException(
                "Failed to decrypt credentials payload. The key may be invalid or the data was corrupted."
            )
