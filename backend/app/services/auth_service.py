"""Authentication service managing admin login, session lifecycle, token rotation, and replay defenses."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.hashing import (
    create_refresh_token,
    hash_secret,
    parse_refresh_token,
    verify_dummy_password,
    verify_password,
)
from app.auth.jwt import create_access_token
from app.core.config import settings
from app.core.logging import logger
from app.models.admin_session import AdminSession
from app.models.admin_user import AdminUser
from app.repositories.admin_session_repository import AdminSessionRepository
from app.repositories.admin_user_repository import AdminUserRepository
from app.services.exceptions import (
    AuthenticationError,
    InvalidRefreshTokenError,
    RefreshTokenReplayError,
)


class AuthService:
    """Service orchestrating admin authentication, session tracking, and token rotation."""

    def __init__(
        self,
        admin_user_repo: Optional[AdminUserRepository] = None,
        session_repo: Optional[AdminSessionRepository] = None,
    ):
        self.admin_user_repo = admin_user_repo or AdminUserRepository()
        self.session_repo = session_repo or AdminSessionRepository()

    async def authenticate_admin(
        self,
        db: AsyncSession,
        email: str,
        password: str,
    ) -> AdminUser:
        """Authenticate admin credentials using Argon2id with constant-time non-existent user handling."""
        clean_email = email.strip().lower()
        admin = await self.admin_user_repo.get_by_email(db, clean_email)

        if not admin:
            # Consume identical CPU time to prevent email enumeration timing attacks
            verify_dummy_password(password)
            logger.warning(f"ADMIN_LOGIN_FAILURE: Unknown email attempt for [{clean_email}]")
            raise AuthenticationError("Invalid email or password.")

        if not verify_password(password, admin.password_hash):
            logger.warning(f"ADMIN_LOGIN_FAILURE: Password mismatch for admin [{admin.public_id}]")
            raise AuthenticationError("Invalid email or password.")

        if not admin.is_active:
            logger.warning(f"ADMIN_LOGIN_FAILURE: Deactivated account login attempt for [{admin.public_id}]")
            # Generic error response to prevent account state enumeration
            raise AuthenticationError("Invalid email or password.")

        # Update last login timestamp
        now_utc = datetime.now(timezone.utc)
        admin.last_login_at = now_utc
        await self.admin_user_repo.update(db, admin)

        logger.info(f"ADMIN_LOGIN_SUCCESS: Authenticated admin [{admin.public_id}] ({clean_email})")
        return admin

    async def create_session(
        self,
        db: AsyncSession,
        admin: AdminUser,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Tuple[str, str, int, AdminUser]:
        """Create a new login session with a composite refresh token and in-memory access token.

        Returns:
            Tuple[raw_refresh_token, access_token, expires_in_seconds, AdminUser]
        """
        now_utc = datetime.now(timezone.utc)
        expires_at = now_utc + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        session_public_id = uuid.uuid4()

        raw_refresh_token, secret_hash = create_refresh_token(session_public_id)

        session = AdminSession(
            public_id=session_public_id,
            admin_user_id=admin.id,
            refresh_token_hash=secret_hash,
            user_agent=user_agent,
            ip_address=ip_address,
            created_at=now_utc,
            last_used_at=now_utc,
            expires_at=expires_at,
            revoked_at=None,
        )
        await self.session_repo.create(db, session)

        access_token = create_access_token(admin.public_id)
        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

        return raw_refresh_token, access_token, expires_in, admin

    async def refresh_session(
        self,
        db: AsyncSession,
        raw_refresh_token: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Tuple[str, str, int, AdminUser]:
        """Rotate a refresh token session and issue a new access token.

        Detects token replay attacks deterministically: if secret hash mismatches current session
        hash, the session is immediately marked revoked and access is rejected.

        Returns:
            Tuple[new_raw_refresh_token, access_token, expires_in_seconds, AdminUser]
        """
        if not raw_refresh_token:
            raise InvalidRefreshTokenError("Authentication required.")

        try:
            session_public_id, raw_secret = parse_refresh_token(raw_refresh_token)
        except ValueError as exc:
            logger.warning(f"ADMIN_REFRESH_REJECTED: Malformed token [{str(exc)}]")
            raise InvalidRefreshTokenError("Invalid refresh token.") from exc

        secret_hash = hash_secret(raw_secret)

        # Lock session row to serialize concurrent rotation attempts
        session = await self.session_repo.get_by_public_id_for_update(db, session_public_id)
        if not session:
            logger.warning(f"ADMIN_REFRESH_REJECTED: Non-existent session [{session_public_id}]")
            raise InvalidRefreshTokenError("Session not found.")

        now_utc = datetime.now(timezone.utc)

        # Validate session revocation
        if session.revoked_at is not None:
            logger.warning(f"ADMIN_REFRESH_REJECTED: Attempt to use revoked session [{session_public_id}]")
            raise InvalidRefreshTokenError("Session revoked.")

        # Validate session expiration
        if session.expires_at <= now_utc:
            logger.warning(f"ADMIN_REFRESH_REJECTED: Session expired [{session_public_id}]")
            raise InvalidRefreshTokenError("Session expired.")

        # Replay Attack Detection: Verify presented secret matches the current session hash
        if secret_hash != session.refresh_token_hash:
            logger.error(
                f"ADMIN_REFRESH_REPLAY_DETECTED: Stale token secret presented for session [{session_public_id}]. "
                f"Revoking session immediately."
            )
            session.revoked_at = now_utc
            await self.session_repo.update(db, session)
            raise RefreshTokenReplayError("Session invalidated due to token reuse.")

        # Validate admin account active status
        admin = await self.admin_user_repo.get_by_id(db, session.admin_user_id)
        if not admin or not admin.is_active:
            logger.warning(f"ADMIN_REFRESH_REJECTED: Inactive admin for session [{session_public_id}]")
            raise InvalidRefreshTokenError("Administrator account is inactive.")

        # Atomic Rotation: Generate new >=256-bit secret and update session record
        new_raw_token, new_secret_hash = create_refresh_token(session.public_id)
        session.refresh_token_hash = new_secret_hash
        session.last_used_at = now_utc
        if user_agent:
            session.user_agent = user_agent
        if ip_address:
            session.ip_address = ip_address

        await self.session_repo.update(db, session)

        access_token = create_access_token(admin.public_id)
        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

        logger.info(f"ADMIN_REFRESH_SUCCESS: Rotated session [{session.public_id}] for admin [{admin.public_id}]")
        return new_raw_token, access_token, expires_in, admin

    async def revoke_session(
        self,
        db: AsyncSession,
        raw_refresh_token: Optional[str],
    ) -> bool:
        """Revoke a single session identified by its refresh token."""
        if not raw_refresh_token:
            return False

        try:
            session_public_id, _ = parse_refresh_token(raw_refresh_token)
        except ValueError:
            return False

        session = await self.session_repo.get_by_public_id_for_update(db, session_public_id)
        if session and session.revoked_at is None:
            session.revoked_at = datetime.now(timezone.utc)
            await self.session_repo.update(db, session)
            logger.info(f"ADMIN_LOGOUT: Revoked session [{session.public_id}] for admin [{session.admin_user_id}]")
            return True

        return False

    async def revoke_all_sessions(
        self,
        db: AsyncSession,
        admin_id: int,
    ) -> int:
        """Revoke all active sessions for a specific admin user."""
        count = await self.session_repo.revoke_all_for_admin(db, admin_id)
        logger.info(f"ADMIN_LOGOUT_ALL: Revoked {count} sessions for admin_id [{admin_id}]")
        return count
