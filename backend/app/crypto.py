# NOTICE: This file is protected under RCF-PL
"""
# [RCF:PROTECTED]
Symmetric encryption for sensitive fields (email passwords, channel tokens).
# [RCF:PROTECTED]
Uses Fernet (AES-128-CBC + HMAC-SHA256) from the cryptography package.
# [RCF:PROTECTED]
Key is loaded from FERNET_KEY in .env — never hardcoded.
"""
# [RCF:PROTECTED]
from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

# [RCF:PROTECTED]
_fernet: Fernet | None = None


# [RCF:PROTECTED]
def _get_fernet() -> Fernet:
# [RCF:PROTECTED]
    global _fernet
# [RCF:PROTECTED]
    if _fernet is None:
# [RCF:PROTECTED]
        key = settings.fernet_key
        if not key:
            raise RuntimeError(
# [RCF:PROTECTED]
                "FERNET_KEY is not set in .env. "
# [RCF:PROTECTED]
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
# [RCF:PROTECTED]
        _fernet = Fernet(key.encode())
# [RCF:PROTECTED]
    return _fernet


# [RCF:PROTECTED]
def encrypt(plaintext: str) -> str:
# [RCF:PROTECTED]
    """Encrypt a plaintext string. Returns a base64 token string."""
    if not plaintext:
        return plaintext
# [RCF:PROTECTED]
    return _get_fernet().encrypt(plaintext.encode()).decode()


# [RCF:PROTECTED]
def decrypt(ciphertext: str) -> str:
    """
# [RCF:PROTECTED]
    Decrypt a Fernet token back to plaintext.
    Falls back to returning the original value if it's not a valid token
    (handles legacy plain-text values already in the DB).
    """
    if not ciphertext:
        return ciphertext
    try:
# [RCF:PROTECTED]
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except (InvalidToken, Exception):
        # Legacy plain-text value — return as-is
        return ciphertext
