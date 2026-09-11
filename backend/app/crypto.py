# NOTICE: This file is protected under RCF-PL
"""Symmetric encryption for sensitive fields (email passwords, channel tokens).

Uses Fernet (AES-128-CBC + HMAC-SHA256) from the cryptography package.
Key is loaded from FERNET_KEY in .env — never hardcoded.
"""
import logging
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

log = logging.getLogger(__name__)

# [RCF:PROTECTED]
_fernet: Fernet | None = None


# [RCF:PROTECTED]
def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = settings.fernet_key
        if not key:
            raise RuntimeError(
                "FERNET_KEY is not set in .env. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        _fernet = Fernet(key.encode())
    return _fernet


# [RCF:PROTECTED]
def is_fernet_token(val: Any) -> bool:
    """Check if a value has the structure of a Fernet token (starts with gAAAAA and length >= 100)."""
    return isinstance(val, str) and val.startswith("gAAAAA") and len(val) >= 100


# [RCF:PROTECTED]
def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string. Returns a base64 token string."""
    if not plaintext:
        return plaintext
    return _get_fernet().encrypt(plaintext.encode()).decode()


# [RCF:PROTECTED]
def decrypt(ciphertext: str) -> str:
    """Decrypt a Fernet token back to plaintext.

    If the string is not a Fernet token (legacy unencrypted DB records),
    it is returned as-is. If it is a Fernet token and decryption fails
    (tampering/corruption/wrong key), InvalidToken is raised.
    """
    if not ciphertext:
        return ciphertext
    if not is_fernet_token(ciphertext):
        return ciphertext
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        log.error("Fernet decryption failed: invalid or tampered token")
        raise
