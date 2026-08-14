"""Integration tests for AuthService workflows, session lifecycle, token rotation, and replay detection."""

import uuid
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.hashing import hash_password
from app.auth.jwt import decode_access_token
from app.models.admin_session import AdminSession
from app.models.admin_user import AdminUser
from app.services.auth_service import AuthService
from app.services.exceptions import (
    AuthenticationError,
    InvalidRefreshTokenError,
    RefreshTokenReplayError,
)


@pytest.mark.asyncio
async def test_authenticate_admin_success(db_session: AsyncSession):
    """Test successful admin authentication and last_login_at update."""
    service = AuthService()
    pwd = "ValidAdminPassword123!"

    admin = AdminUser(
        public_id=uuid.uuid4(),
        email="auth.test@samagra.org",
        password_hash=hash_password(pwd),
        full_name="Auth Tester",
        is_active=True,
    )
    db_session.add(admin)
    await db_session.flush()

    authenticated = await service.authenticate_admin(
        db_session,
        email="AUTH.TEST@samagra.org ",  # Test case and whitespace normalization
        password=pwd,
    )

    assert authenticated.id == admin.id
    assert authenticated.last_login_at is not None


@pytest.mark.asyncio
async def test_authenticate_admin_failures(db_session: AsyncSession):
    """Test authentication failures return generic errors to prevent user enumeration."""
    service = AuthService()
    pwd = "ValidAdminPassword123!"

    admin = AdminUser(
        public_id=uuid.uuid4(),
        email="existing.admin@samagra.org",
        password_hash=hash_password(pwd),
        full_name="Existing Admin",
        is_active=True,
    )
    inactive_admin = AdminUser(
        public_id=uuid.uuid4(),
        email="inactive.admin@samagra.org",
        password_hash=hash_password(pwd),
        full_name="Inactive Admin",
        is_active=False,
    )
    db_session.add_all([admin, inactive_admin])
    await db_session.flush()

    # 1. Non-existent email
    with pytest.raises(AuthenticationError, match="Invalid email or password"):
        await service.authenticate_admin(db_session, "nonexistent@samagra.org", pwd)

    # 2. Incorrect password
    with pytest.raises(AuthenticationError, match="Invalid email or password"):
        await service.authenticate_admin(db_session, "existing.admin@samagra.org", "WrongPassword123!")

    # 3. Deactivated account
    with pytest.raises(AuthenticationError, match="Invalid email or password"):
        await service.authenticate_admin(db_session, "inactive.admin@samagra.org", pwd)


@pytest.mark.asyncio
async def test_create_and_refresh_session_workflow(db_session: AsyncSession):
    """Test full login session creation, token issuance, and successful rotation."""
    service = AuthService()
    pwd = "ValidPassword123!"

    admin = AdminUser(
        public_id=uuid.uuid4(),
        email="session.admin@samagra.org",
        password_hash=hash_password(pwd),
        full_name="Session Admin",
        is_active=True,
    )
    db_session.add(admin)
    await db_session.flush()

    # 1. Create session
    raw_refresh, access_token, expires_in, user = await service.create_session(
        db_session,
        admin=admin,
        user_agent="Pytest-Agent/1.0",
        ip_address="127.0.0.1",
    )

    assert raw_refresh is not None
    assert access_token is not None
    assert expires_in == 900
    assert user.id == admin.id

    # Verify access token
    payload = decode_access_token(access_token)
    assert payload["public_id"] == str(admin.public_id)

    # 2. Rotate session
    new_raw_refresh, new_access_token, new_expires_in, user_after = await service.refresh_session(
        db_session,
        raw_refresh_token=raw_refresh,
        user_agent="Pytest-Agent/1.1",
        ip_address="127.0.0.2",
    )

    assert new_raw_refresh is not None
    assert new_raw_refresh != raw_refresh
    assert new_access_token is not None


@pytest.mark.asyncio
async def test_refresh_replay_detection_revokes_session(db_session: AsyncSession):
    """Test that re-using an old rotated refresh token triggers replay detection and revokes the session."""
    service = AuthService()
    admin = AdminUser(
        public_id=uuid.uuid4(),
        email="replay.admin@samagra.org",
        password_hash=hash_password("pwd"),
        full_name="Replay Admin",
        is_active=True,
    )
    db_session.add(admin)
    await db_session.flush()

    # Step 1: Login (Token A issued)
    token_a, _, _, _ = await service.create_session(db_session, admin)

    # Step 2: Refresh (Token A rotated -> Token B issued)
    token_b, _, _, _ = await service.refresh_session(db_session, token_a)
    assert token_b != token_a

    # Step 3: Replay attack with old Token A
    with pytest.raises(RefreshTokenReplayError, match="Session invalidated due to token reuse"):
        await service.refresh_session(db_session, token_a)

    # Step 4: Verify Token B is now ALSO rejected because the compromised session was revoked
    with pytest.raises(InvalidRefreshTokenError, match="Session revoked"):
        await service.refresh_session(db_session, token_b)


@pytest.mark.asyncio
async def test_refresh_expired_or_revoked_session(db_session: AsyncSession):
    """Test refresh failure on expired or revoked sessions."""
    service = AuthService()
    admin = AdminUser(
        public_id=uuid.uuid4(),
        email="expired.admin@samagra.org",
        password_hash=hash_password("pwd"),
        full_name="Expired Admin",
        is_active=True,
    )
    db_session.add(admin)
    await db_session.flush()

    token, _, _, _ = await service.create_session(db_session, admin)

    # Revoke session
    revoked = await service.revoke_session(db_session, token)
    assert revoked is True

    # Refresh after revocation fails
    with pytest.raises(InvalidRefreshTokenError, match="Session revoked"):
        await service.refresh_session(db_session, token)


@pytest.mark.asyncio
async def test_revoke_all_sessions_for_admin(db_session: AsyncSession):
    """Test revoking all active sessions for a specific administrator."""
    service = AuthService()
    admin = AdminUser(
        public_id=uuid.uuid4(),
        email="multi.admin@samagra.org",
        password_hash=hash_password("pwd"),
        full_name="Multi Admin",
        is_active=True,
    )
    db_session.add(admin)
    await db_session.flush()

    token_1, _, _, _ = await service.create_session(db_session, admin)
    token_2, _, _, _ = await service.create_session(db_session, admin)

    revoked_count = await service.revoke_all_sessions(db_session, admin.id)
    assert revoked_count == 2

    # Both tokens should now fail
    with pytest.raises(InvalidRefreshTokenError, match="Session revoked"):
        await service.refresh_session(db_session, token_1)

    with pytest.raises(InvalidRefreshTokenError, match="Session revoked"):
        await service.refresh_session(db_session, token_2)
