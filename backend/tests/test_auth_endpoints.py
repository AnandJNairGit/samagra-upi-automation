"""HTTP endpoint integration tests for Auth & Admin APIs."""

import uuid
import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.hashing import hash_password
from app.auth.jwt import create_access_token
from app.auth.rate_limiter import auth_rate_limiter
from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.admin_user import AdminUser


@pytest.fixture(autouse=True)
def setup_test_environment(db_session: AsyncSession):
    """Reset rate limiter and bind test database session to FastAPI dependency."""
    auth_rate_limiter.reset()
    app.dependency_overrides[get_db] = lambda: db_session
    yield
    auth_rate_limiter.reset()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_login_endpoint_success(db_session: AsyncSession):
    """Test POST /v1/auth/login success and cookie issuance."""
    pwd = "SecureAdminPassword123!"
    admin = AdminUser(
        public_id=uuid.uuid4(),
        email="api.admin@samagra.org",
        password_hash=hash_password(pwd),
        full_name="API Admin",
        is_active=True,
    )
    db_session.add(admin)
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/login",
            json={"email": "api.admin@samagra.org", "password": pwd},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 900
        assert data["admin"]["email"] == "api.admin@samagra.org"
        assert data["admin"]["full_name"] == "API Admin"

        # Verify HttpOnly refresh cookie is set
        cookies = response.cookies
        assert settings.AUTH_COOKIE_NAME in cookies


@pytest.mark.asyncio
async def test_login_endpoint_failure_generic_error(db_session: AsyncSession):
    """Test POST /v1/auth/login failure returns 401 with generic message."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/auth/login",
            json={"email": "nonexistent@samagra.org", "password": "wrongpassword123"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password."


@pytest.mark.asyncio
async def test_login_rate_limiting(db_session: AsyncSession):
    """Test rate limiting on POST /v1/auth/login triggers HTTP 429 with Retry-After header."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # First 5 attempts should return 401 (unauthorized)
        for _ in range(5):
            res = await client.post(
                "/v1/auth/login",
                json={"email": "ratelimit@samagra.org", "password": "wrongpassword123"},
            )
            assert res.status_code == 401

        # 6th attempt should be rate limited (429)
        res_blocked = await client.post(
            "/v1/auth/login",
            json={"email": "ratelimit@samagra.org", "password": "wrongpassword123"},
        )
        assert res_blocked.status_code == 429
        assert "Retry-After" in res_blocked.headers
        assert "Too many login attempts" in res_blocked.json()["detail"]


@pytest.mark.asyncio
async def test_refresh_and_logout_endpoints(db_session: AsyncSession):
    """Test POST /v1/auth/refresh and POST /v1/auth/logout workflows."""
    pwd = "SecurePassword123!"
    admin = AdminUser(
        public_id=uuid.uuid4(),
        email="refresh.flow@samagra.org",
        password_hash=hash_password(pwd),
        full_name="Refresh Flow Admin",
        is_active=True,
    )
    db_session.add(admin)
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login to get cookie
        login_res = await client.post(
            "/v1/auth/login",
            json={"email": "refresh.flow@samagra.org", "password": pwd},
        )
        assert login_res.status_code == 200
        refresh_cookie = login_res.cookies.get(settings.AUTH_COOKIE_NAME)
        assert refresh_cookie is not None

        # 2. Refresh token (Notice: NO Authorization header needed!)
        client.cookies.set(settings.AUTH_COOKIE_NAME, refresh_cookie)
        refresh_res = await client.post("/v1/auth/refresh")

        assert refresh_res.status_code == 200
        new_data = refresh_res.json()
        assert "access_token" in new_data
        assert new_data["admin"]["email"] == "refresh.flow@samagra.org"

        # 3. Logout
        logout_res = await client.post("/v1/auth/logout")
        assert logout_res.status_code == 200

        # 4. Refresh after logout should fail
        fail_res = await client.post("/v1/auth/refresh")
        assert fail_res.status_code == 401


@pytest.mark.asyncio
async def test_protected_admin_routes_authorization(db_session: AsyncSession):
    """Test that /v1/auth/me and /v1/admin/health require valid Bearer token."""
    pwd = "SecurePassword123!"
    admin = AdminUser(
        public_id=uuid.uuid4(),
        email="protected.admin@samagra.org",
        password_hash=hash_password(pwd),
        full_name="Protected Admin",
        is_active=True,
    )
    inactive_admin = AdminUser(
        public_id=uuid.uuid4(),
        email="inactive.guard@samagra.org",
        password_hash=hash_password(pwd),
        full_name="Inactive Guard",
        is_active=False,
    )
    db_session.add_all([admin, inactive_admin])
    await db_session.flush()

    valid_token = create_access_token(admin.public_id)
    inactive_token = create_access_token(inactive_admin.public_id)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unauthenticated request -> 401
        res_no_auth = await client.get("/v1/admin/health")
        assert res_no_auth.status_code == 401

        # 2. Inactive admin token -> 401
        res_inactive = await client.get(
            "/v1/admin/health",
            headers={"Authorization": f"Bearer {inactive_token}"},
        )
        assert res_inactive.status_code == 401

        # 3. Valid active admin token -> 200 OK
        res_auth = await client.get(
            "/v1/admin/health",
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert res_auth.status_code == 200
        data = res_auth.json()
        assert data["status"] == "ok"
        assert data["authenticated"] is True
        assert data["admin_email"] == "protected.admin@samagra.org"

        # 4. /v1/auth/me profile query -> 200 OK
        res_me = await client.get(
            "/v1/auth/me",
            headers={"Authorization": f"Bearer {valid_token}"},
        )
        assert res_me.status_code == 200
        me_data = res_me.json()
        assert me_data["email"] == "protected.admin@samagra.org"
        assert me_data["is_active"] is True
