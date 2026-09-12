# NOTICE: This file is protected under RCF-PL
import pytest
from cryptography.fernet import InvalidToken
from pathlib import Path
from app.crypto import decrypt, encrypt, is_fernet_token


def test_is_fernet_token():
    # Real Fernet token
    token = encrypt("secret_value")
    assert is_fernet_token(token)

    # Legacy plain strings
    assert not is_fernet_token("plaintext_password")
    assert not is_fernet_token("gAAAAA_too_short")
    assert not is_fernet_token("")
    assert not is_fernet_token(None)
    assert not is_fernet_token(123)


def test_decrypt_valid_and_legacy():
    # Valid token decrypts
    token = encrypt("my_super_secret")
    assert decrypt(token) == "my_super_secret"

    # Legacy plain string returns unchanged
    assert decrypt("plain_unencrypted_token") == "plain_unencrypted_token"
    assert decrypt("") == ""


def test_decrypt_tampered_token_raises():
    token = encrypt("my_super_secret")
    # Tamper with the token (change characters in payload)
    tampered = token[:10] + ("X" if token[10] != "X" else "Y") + token[11:]
    assert is_fernet_token(tampered)
    with pytest.raises(InvalidToken):
        decrypt(tampered)


def test_path_traversal_validation_relative_to():
    # Detect workspace root from this file's location: tests/ → repo root
    base_dir = Path(__file__).resolve().parent.parent.parent

    # Valid inside workspace
    valid_path = (base_dir / "backend/app").resolve()
    assert valid_path.is_relative_to(base_dir)

    # Traversal attempts outside workspace
    traversal_path = (base_dir / "../../../etc/passwd").resolve()
    assert not traversal_path.is_relative_to(base_dir)

    # Sibling directory attack (e.g. /workspaces/AladdinAI_fake vs /workspaces/AladdinAI)
    sibling_path = (base_dir.parent / "AladdinAI_fake" / "secret").resolve()
    assert not sibling_path.is_relative_to(base_dir)
