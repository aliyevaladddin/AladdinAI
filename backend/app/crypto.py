"""
Symmetric encryption for sensitive fields (email passwords, channel tokens).
Uses Fernet (AES-128-CBC + HMAC-SHA256) from the cryptography package.
Key is loaded from FERNET_KEY in .env — never hardcoded.
"""
from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

_fernet: Fernet | None = None


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


def encrypt(plaintext: str) -> str:
    """Encrypt a plaintext string. Returns a base64 token string."""
    if not plaintext:
        return plaintext
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """
    Decrypt a Fernet token back to plaintext.
    Falls back to returning the original value if it's not a valid token
    (handles legacy plain-text values already in the DB).
    """
    if not ciphertext:
        return ciphertext
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except (InvalidToken, Exception):
        # Legacy plain-text value — return as-is
        return ciphertext
