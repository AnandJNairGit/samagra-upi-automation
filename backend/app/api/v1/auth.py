"""Authentication API router handling admin login, refresh rotation, logout, and profile queries."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.dependencies import get_auth_service, get_client_ip, get_user_agent, require_admin
from app.auth.rate_limiter import auth_rate_limiter
from app.core.config import settings
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.auth import (
    AdminProfileResponse,
    LoginRequest,
    LoginResponse,
)
from app.services.auth_service import AuthService
from app.services.exceptions import (
    AuthenticationError,
    InvalidRefreshTokenError,
    RefreshTokenReplayError,
)

router = APIRouter()


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin Login",
)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Authenticate admin credentials, establish session, set HttpOnly cookie, and issue access token."""
    client_ip = get_client_ip(request) or "unknown"
    user_agent = get_user_agent(request)
    normalized_email = payload.email.strip().lower()

    # Rate limiting: Max 5 attempts per 60 seconds per IP + normalized email
    rate_key = f"login:{client_ip}:{normalized_email}"
    allowed, retry_after = auth_rate_limiter.check(rate_key, max_requests=5, window_seconds=60)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    try:
        admin = await auth_service.authenticate_admin(
            db=db,
            email=payload.email,
            password=payload.password,
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    raw_refresh, access_token, expires_in, admin = await auth_service.create_session(
        db=db,
        admin=admin,
        user_agent=user_agent,
        ip_address=client_ip if client_ip != "unknown" else None,
    )

    # Set secure HttpOnly cookie containing composite refresh token
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=raw_refresh,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        path="/upi-api/",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
        admin=AdminProfileResponse.model_validate(admin),
    )


@router.post(
    "/refresh",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate Refresh Token & Issue Access Token",
)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Authenticate purely via HttpOnly refresh cookie, rotate session token, and return new access token."""
    client_ip = get_client_ip(request) or "unknown"
    user_agent = get_user_agent(request)

    # Rate limiting: Max 30 refresh attempts per 60 seconds per IP
    rate_key = f"refresh:{client_ip}"
    allowed, retry_after = auth_rate_limiter.check(rate_key, max_requests=30, window_seconds=60)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many refresh requests. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    raw_refresh = request.cookies.get(settings.AUTH_COOKIE_NAME)
    if not raw_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        new_raw_token, access_token, expires_in, admin = await auth_service.refresh_session(
            db=db,
            raw_refresh_token=raw_refresh,
            user_agent=user_agent,
            ip_address=client_ip if client_ip != "unknown" else None,
        )
    except (InvalidRefreshTokenError, RefreshTokenReplayError) as exc:
        # Clear invalid/replayed cookie
        response.delete_cookie(
            key=settings.AUTH_COOKIE_NAME,
            path="/upi-api/",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    # Set newly rotated refresh token in HttpOnly cookie
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=new_raw_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        path="/upi-api/",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
        admin=AdminProfileResponse.model_validate(admin),
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Admin Logout",
)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Revoke current admin session and clear refresh cookie."""
    raw_refresh = request.cookies.get(settings.AUTH_COOKIE_NAME)
    if raw_refresh:
        await auth_service.revoke_session(db, raw_refresh)

    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        path="/upi-api/",
    )
    return {"status": "ok", "message": "Successfully logged out."}


@router.post(
    "/logout-all",
    status_code=status.HTTP_200_OK,
    summary="Admin Logout All Sessions",
)
async def logout_all(
    response: Response,
    current_admin: AdminUser = require_admin,
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Revoke all active sessions for current admin and clear refresh cookie."""
    revoked_count = await auth_service.revoke_all_sessions(db, current_admin.id)

    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        path="/upi-api/",
    )
    return {
        "status": "ok",
        "message": f"Successfully revoked {revoked_count} active sessions.",
    }


@router.get(
    "/me",
    response_model=AdminProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Current Admin Profile",
)
async def get_me(
    current_admin: AdminUser = require_admin,
):
    """Retrieve profile of currently authenticated administrator."""
    return AdminProfileResponse.model_validate(current_admin)
