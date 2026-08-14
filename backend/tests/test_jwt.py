"""Unit tests for JWT access token encoding, decoding, and claim verification."""

import uuid
from datetime import timedelta
import jwt
import pytest
from app.auth.jwt import (
    InvalidTokenError,
    TokenExpiredError,
    create_access_token,
    decode_access_token,
)
from app.core.config import settings


def test_create_and_decode_access_token():
    """Test standard access token lifecycle with valid claims."""
    admin_public_id = uuid.uuid4()
    token = create_access_token(admin_public_id, expires_delta=timedelta(minutes=15))

    assert token is not None
    assert isinstance(token, str)

    payload = decode_access_token(token)
    assert payload["sub"] == str(admin_public_id)
    assert payload["public_id"] == str(admin_public_id)
    assert payload["token_type"] == "access"
    assert "iat" in payload
    assert "exp" in payload
    assert payload["exp"] > payload["iat"]


def test_expired_access_token_raises():
    """Test that expired access token raises TokenExpiredError."""
    admin_public_id = uuid.uuid4()
    # Expire token immediately (1 second ago)
    token = create_access_token(admin_public_id, expires_delta=timedelta(seconds=-1))

    with pytest.raises(TokenExpiredError, match="Access token has expired"):
        decode_access_token(token)


def test_invalid_signature_raises():
    """Test that token signed with a different key raises InvalidTokenError."""
    admin_public_id = uuid.uuid4()
    token = jwt.encode(
        {"sub": str(admin_public_id), "public_id": str(admin_public_id), "token_type": "access", "iat": 1000, "exp": 9999999999},
        "wrong_secret_key_different_from_settings_12345",
        algorithm="HS256",
    )

    with pytest.raises(InvalidTokenError, match="Invalid access token"):
        decode_access_token(token)


def test_wrong_token_type_raises():
    """Test that token with unexpected token_type claim raises InvalidTokenError."""
    admin_public_id = uuid.uuid4()
    token = jwt.encode(
        {"sub": str(admin_public_id), "public_id": str(admin_public_id), "token_type": "refresh", "iat": 1000, "exp": 9999999999},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(InvalidTokenError, match="Expected access token"):
        decode_access_token(token)


def test_empty_or_malformed_token():
    """Test empty token raises InvalidTokenError."""
    with pytest.raises(InvalidTokenError, match="Token is missing or empty"):
        decode_access_token("")

    with pytest.raises(InvalidTokenError, match="Invalid access token"):
        decode_access_token("not.a.valid.jwt.token")
