# NOTICE: This file is protected under RCF-PL
import pytest
from fastapi import HTTPException
from jose import jwt
from pydantic import ValidationError

from app.config import settings
from app.schemas.auth import RegisterRequest
from app.security import (
    create_access_token,
    decode_token,
)


def test_decode_token_valid():
    token = create_access_token(42)
    user_id = decode_token(token, expected_type="access")
    assert user_id == 42


def test_decode_token_wrong_type():
    token = create_access_token(42)
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token, expected_type="refresh")
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid token type"


def test_decode_token_non_numeric_sub():
    # Construct a token with non-numeric sub
    payload = {"sub": "not-an-integer", "type": "access"}
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    with pytest.raises(HTTPException) as exc_info:
        decode_token(token, expected_type="access")
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid token"


def test_decode_token_missing_sub():
    payload = {"type": "access"}
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    with pytest.raises(HTTPException) as exc_info:
        decode_token(token, expected_type="access")
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid token"


def test_register_schema_password_length():
    # Valid password
    req = RegisterRequest(email="test@example.com", password="password123", name="Test User")
    assert req.password == "password123"

    # Too short (< 8 chars)
    with pytest.raises(ValidationError):
        RegisterRequest(email="test@example.com", password="short", name="Test User")

    # Too long (> 128 chars)
    with pytest.raises(ValidationError):
        RegisterRequest(email="test@example.com", password="a" * 129, name="Test User")
