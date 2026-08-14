"""FastAPI dependency providers for authentication, authorization, and client metadata."""

import uuid
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.jwt import InvalidTokenError, TokenExpiredError, decode_access_token
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.repositories.admin_user_repository import AdminUserRepository

# HTTP Bearer scheme without auto_error to control exact status codes & headers
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    """Validate Bearer access token and resolve active AdminUser from database.

    Raises 401 Unauthorized for missing, expired, invalid tokens or inactive admins.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except TokenExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired.",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\", error_description=\"The access token expired\""},
        ) from exc
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token.",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        ) from exc

    public_id_str = payload.get("public_id") or payload.get("sub")
    if not public_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        admin_public_id = uuid.UUID(str(public_id_str))
    except (ValueError, AttributeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed user identifier in token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    admin_repo = AdminUserRepository()
    admin = await admin_repo.get_by_public_id(db, admin_public_id)

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Administrator account not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Administrator account is deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return admin


# Reusable dependency for all protected admin endpoints
require_admin = Depends(get_current_admin)


def get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP address, checking X-Forwarded-For if reverse-proxied."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first client IP in the proxy chain
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def get_user_agent(request: Request) -> Optional[str]:
    """Extract User-Agent header from incoming request."""
    return request.headers.get("User-Agent")


def get_auth_service() -> "AuthService":
    """Factory dependency for AuthService instance."""
    from app.services.auth_service import AuthService
    return AuthService()
