"""Password hashing and cryptographic token utilities using Argon2id and SHA-256."""

import hashlib
import secrets
import uuid
from typing import Tuple
import argon2
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

# Argon2id password hasher configured with OWASP recommended parameters
_password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MiB
    parallelism=4,
    hash_len=32,
    type=argon2.Type.ID,
)

# Precomputed dummy Argon2id hash generated with the exact same parameters
# Used to enforce constant-time response behavior when user email is not found
DUMMY_ARGON2_HASH: str = _password_hasher.hash("dummy_constant_password_to_prevent_timing_attacks_123")


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    if not password:
        raise ValueError("Password cannot be empty.")
    return _password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2id hash."""
    if not plain_password or not hashed_password:
        return False
    try:
        return _password_hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def verify_dummy_password(password: str) -> bool:
    """Consume constant CPU time verifying against a dummy hash for non-existent users."""
    try:
        _password_hasher.verify(DUMMY_ARGON2_HASH, password or "dummy")
    except Exception:
        pass
    return False


def hash_secret(raw_secret: str) -> str:
    """Compute SHA-256 hex digest of a raw token secret."""
    if not raw_secret:
        raise ValueError("Secret cannot be empty.")
    return hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()


def create_refresh_token(session_public_id: uuid.UUID) -> Tuple[str, str]:
    """Generate a composite refresh token and its SHA-256 secret hash.

    Format: <session_public_id_hex>.<random_secret>
    Entropy: >= 256 bits via secrets.token_urlsafe(32)
    Returns: (raw_refresh_token, secret_sha256_hash)
    """
    random_secret = secrets.token_urlsafe(32)
    secret_hash = hash_secret(random_secret)
    raw_token = f"{session_public_id.hex}.{random_secret}"
    return raw_token, secret_hash


def parse_refresh_token(raw_token: str) -> Tuple[uuid.UUID, str]:
    """Parse a composite refresh token into session public_id and raw secret.

    Raises: ValueError if token format is malformed or UUID is invalid.
    """
    if not raw_token or "." not in raw_token:
        raise ValueError("Invalid refresh token format.")

    parts = raw_token.strip().split(".", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("Malformed refresh token components.")

    try:
        session_public_id = uuid.UUID(hex=parts[0])
    except (ValueError, AttributeError) as exc:
        raise ValueError("Invalid session identifier in refresh token.") from exc

    return session_public_id, parts[1]
