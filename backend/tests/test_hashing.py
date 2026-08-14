"""Unit tests for password hashing, timing-attack defense, and composite refresh token utilities."""

import uuid
import pytest
from app.auth.hashing import (
    create_refresh_token,
    hash_password,
    hash_secret,
    parse_refresh_token,
    verify_dummy_password,
    verify_password,
)


def test_argon2_password_hashing():
    """Test Argon2id password hashing and verification."""
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)

    assert hashed is not None
    assert hashed.startswith("$argon2id$")
    assert hashed != password

    # Valid password verification
    assert verify_password(password, hashed) is True

    # Invalid password verification
    assert verify_password("WrongPassword123!", hashed) is False
    assert verify_password("", hashed) is False
    assert verify_password(password, "") is False


def test_argon2_empty_password_raises():
    """Test that hashing an empty password raises ValueError."""
    with pytest.raises(ValueError, match="Password cannot be empty"):
        hash_password("")


def test_dummy_password_verification():
    """Test constant-time dummy verification helper returns False without raising exceptions."""
    result = verify_dummy_password("any_password_attempt_123")
    assert result is False

    result_empty = verify_dummy_password("")
    assert result_empty is False


def test_secret_hashing():
    """Test SHA-256 token secret hashing."""
    secret = "random_entropy_secret_string"
    hashed = hash_secret(secret)

    assert len(hashed) == 64
    assert hashed == hash_secret(secret)
    assert hashed != hash_secret("different_secret")


def test_create_and_parse_refresh_token():
    """Test composite refresh token creation and parsing."""
    session_id = uuid.uuid4()
    raw_token, secret_hash = create_refresh_token(session_id)

    assert raw_token is not None
    assert "." in raw_token
    assert len(secret_hash) == 64

    parsed_id, raw_secret = parse_refresh_token(raw_token)
    assert parsed_id == session_id
    assert hash_secret(raw_secret) == secret_hash


def test_parse_invalid_refresh_tokens():
    """Test parse_refresh_token validation on malformed tokens."""
    with pytest.raises(ValueError, match="Invalid refresh token format"):
        parse_refresh_token("")

    with pytest.raises(ValueError, match="Invalid refresh token format"):
        parse_refresh_token("no_dot_in_token")

    with pytest.raises(ValueError, match="Malformed refresh token components"):
        parse_refresh_token(".missing_id")

    with pytest.raises(ValueError, match="Malformed refresh token components"):
        parse_refresh_token("missing_secret.")

    with pytest.raises(ValueError, match="Invalid session identifier"):
        parse_refresh_token("not_a_valid_uuid_hex.secret123")
