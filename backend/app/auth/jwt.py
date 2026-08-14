"""JWT Access Token creation, decoding, and verification."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
from app.core.config import settings


class JWTError(Exception):
    """Base exception for JWT processing failures."""
    pass


class TokenExpiredError(JWTError):
    """Raised when access token expiration time has passed."""
    pass


class InvalidTokenError(JWTError):
    """Raised when token signature, claims, or format are invalid."""
    pass


def create_access_token(
    admin_public_id: uuid.UUID,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a short-lived signed JWT access token.

    Contains minimal claims: sub, public_id, token_type, iat, exp.
    """
    now_utc = datetime.now(timezone.utc)
    expire_duration = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire_time = now_utc + expire_duration

    payload: Dict[str, Any] = {
        "sub": str(admin_public_id),
        "public_id": str(admin_public_id),
        "token_type": "access",
        "iat": int(now_utc.timestamp()),
        "exp": int(expire_time.timestamp()),
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token.

    Verifies signature, expiration, and token_type == 'access'.
    Raises TokenExpiredError or InvalidTokenError.
    """
    if not token:
        raise InvalidTokenError("Token is missing or empty.")

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError("Access token has expired.") from exc
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(f"Invalid access token: {str(exc)}") from exc

    if payload.get("token_type") != "access":
        raise InvalidTokenError("Invalid token type. Expected access token.")

    return payload
