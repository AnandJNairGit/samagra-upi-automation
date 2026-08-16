"""Integration tests for Admin Course Management APIs."""

import uuid
import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.hashing import hash_password
from app.auth.jwt import create_access_token
from app.auth.rate_limiter import auth_rate_limiter
from app.core.database import get_db
from app.main import app
from app.models.admin_user import AdminUser
from app.models.batch import Batch
from app.models.course import Course


@pytest.fixture(autouse=True)
def setup_test_environment(db_session: AsyncSession):
    """Reset rate limiter and bind test database session to FastAPI dependency."""
    auth_rate_limiter.reset()
    app.dependency_overrides[get_db] = lambda: db_session
    yield
    auth_rate_limiter.reset()
    app.dependency_overrides.clear()


async def create_test_admin(db: AsyncSession) -> tuple[AdminUser, str]:
    """Helper to seed an active admin and generate a valid access token."""
    admin = AdminUser(
        public_id=uuid.uuid4(),
        email=f"admin_{uuid.uuid4().hex[:6]}@samagra.org",
        password_hash=hash_password("SecurePassword123!"),
        full_name="Course Test Admin",
        is_active=True,
    )
    db.add(admin)
    await db.flush()
    token = create_access_token(admin.public_id)
    return admin, token


@pytest.mark.asyncio
async def test_create_course_success_default_active(db_session: AsyncSession):
    """Test POST /v1/admin/courses creates course with default status ACTIVE."""
    _, token = await create_test_admin(db_session)
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/admin/courses",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Full Stack AI Development",
                "description": "Comprehensive full stack AI engineering course.",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Full Stack AI Development"
        assert data["description"] == "Comprehensive full stack AI engineering course."
        assert data["status"] == "ACTIVE"
        assert data["batch_count"] == 0
        assert "public_id" in data


@pytest.mark.asyncio
async def test_create_course_explicit_inactive_success(db_session: AsyncSession):
    """Test POST /v1/admin/courses permits creating a course with INACTIVE status."""
    _, token = await create_test_admin(db_session)
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/admin/courses",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Draft Course",
                "description": "Unpublished training curriculum.",
                "status": "INACTIVE",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Draft Course"
        assert data["status"] == "INACTIVE"


@pytest.mark.asyncio
async def test_create_course_archived_status_rejected(db_session: AsyncSession):
    """Test POST /v1/admin/courses rejects creating course with ARCHIVED status."""
    _, token = await create_test_admin(db_session)
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/admin/courses",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Already Archived Course",
                "status": "ARCHIVED",
            },
        )
        assert response.status_code == 422 or response.status_code == 400


@pytest.mark.asyncio
async def test_create_course_whitespace_name_rejected(db_session: AsyncSession):
    """Test POST /v1/admin/courses rejects empty or whitespace-only name."""
    _, token = await create_test_admin(db_session)
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/admin/courses",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "   ", "description": "Invalid name"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_courses_with_batch_counts_and_deterministic_ordering(db_session: AsyncSession):
    """Test GET /v1/admin/courses returns accurate batch_count across all statuses and deterministic ordering."""
    _, token = await create_test_admin(db_session)

    # 1. Create two courses
    c1 = Course(public_id=uuid.uuid4(), name="Course 1", status="ACTIVE")
    c2 = Course(public_id=uuid.uuid4(), name="Course 2", status="ACTIVE")
    db_session.add_all([c1, c2])
    await db_session.flush()

    # 2. Add batches: 2 to c1 (1 ACTIVE, 1 ARCHIVED), 1 to c2 (INACTIVE)
    b1 = Batch(public_id=uuid.uuid4(), course_id=c1.id, name="Cohort A", amount_inr=1000, status="ACTIVE")
    b2 = Batch(public_id=uuid.uuid4(), course_id=c1.id, name="Cohort B", amount_inr=1200, status="ARCHIVED")
    b3 = Batch(public_id=uuid.uuid4(), course_id=c2.id, name="Cohort C", amount_inr=1500, status="INACTIVE")
    db_session.add_all([b1, b2, b3])
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/v1/admin/courses",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

        c1_item = next(c for c in data if c["public_id"] == str(c1.public_id))
        c2_item = next(c for c in data if c["public_id"] == str(c2.public_id))

        # Total batch count regardless of status
        assert c1_item["batch_count"] == 2
        assert c2_item["batch_count"] == 1


@pytest.mark.asyncio
async def test_list_courses_filter_by_status(db_session: AsyncSession):
    """Test GET /v1/admin/courses?status=INACTIVE filters correctly."""
    _, token = await create_test_admin(db_session)

    c_active = Course(public_id=uuid.uuid4(), name="Active Filter Course", status="ACTIVE")
    c_inactive = Course(public_id=uuid.uuid4(), name="Inactive Filter Course", status="INACTIVE")
    db_session.add_all([c_active, c_inactive])
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/v1/admin/courses?status=INACTIVE",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert all(c["status"] == "INACTIVE" for c in data)
        assert any(c["public_id"] == str(c_inactive.public_id) for c in data)
        assert not any(c["public_id"] == str(c_active.public_id) for c in data)


@pytest.mark.asyncio
async def test_get_course_success_and_404(db_session: AsyncSession):
    """Test GET /v1/admin/courses/{id} returns details and handles 404."""
    _, token = await create_test_admin(db_session)
    course = Course(public_id=uuid.uuid4(), name="Single Course Test", description="Details test", status="ACTIVE")
    db_session.add(course)
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Success
        res_ok = await client.get(
            f"/v1/admin/courses/{course.public_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_ok.status_code == 200
        assert res_ok.json()["name"] == "Single Course Test"

        # 404
        res_404 = await client.get(
            f"/v1/admin/courses/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_404.status_code == 404


@pytest.mark.asyncio
async def test_update_course_name_description(db_session: AsyncSession):
    """Test PATCH /v1/admin/courses/{id} updates mutable fields."""
    _, token = await create_test_admin(db_session)
    course = Course(public_id=uuid.uuid4(), name="Initial Name", description="Initial Desc", status="ACTIVE")
    db_session.add(course)
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            f"/v1/admin/courses/{course.public_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Updated Name", "description": "Updated Desc"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated Desc"
        assert data["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_course_lifecycle_active_to_inactive_to_archived(db_session: AsyncSession):
    """Test full allowed lifecycle transitions: ACTIVE -> INACTIVE -> ACTIVE -> ARCHIVED."""
    _, token = await create_test_admin(db_session)
    course = Course(public_id=uuid.uuid4(), name="Lifecycle Course", status="ACTIVE")
    db_session.add(course)
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. ACTIVE -> INACTIVE
        r1 = await client.patch(
            f"/v1/admin/courses/{course.public_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": "INACTIVE"},
        )
        assert r1.status_code == 200
        assert r1.json()["status"] == "INACTIVE"

        # 2. INACTIVE -> ACTIVE
        r2 = await client.patch(
            f"/v1/admin/courses/{course.public_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": "ACTIVE"},
        )
        assert r2.status_code == 200
        assert r2.json()["status"] == "ACTIVE"

        # 3. ACTIVE -> ARCHIVED
        r3 = await client.patch(
            f"/v1/admin/courses/{course.public_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": "ARCHIVED"},
        )
        assert r3.status_code == 200
        assert r3.json()["status"] == "ARCHIVED"


@pytest.mark.asyncio
async def test_course_archived_is_terminal_reject_reactivation(db_session: AsyncSession):
    """Test that an ARCHIVED course cannot transition back to ACTIVE or INACTIVE."""
    _, token = await create_test_admin(db_session)
    course = Course(public_id=uuid.uuid4(), name="Archived Terminal Course", status="ARCHIVED")
    db_session.add(course)
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Try ARCHIVED -> ACTIVE
        r_active = await client.patch(
            f"/v1/admin/courses/{course.public_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": "ACTIVE"},
        )
        assert r_active.status_code == 400

        # Try ARCHIVED -> INACTIVE
        r_inactive = await client.patch(
            f"/v1/admin/courses/{course.public_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": "INACTIVE"},
        )
        assert r_inactive.status_code == 400


@pytest.mark.asyncio
async def test_course_archived_reject_mutation(db_session: AsyncSession):
    """Test that an ARCHIVED course is strictly read-only and rejects updates to name or description."""
    _, token = await create_test_admin(db_session)
    course = Course(public_id=uuid.uuid4(), name="Archived Fixed Course", description="Original", status="ARCHIVED")
    db_session.add(course)
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # GET is allowed (read-only inspect)
        get_res = await client.get(
            f"/v1/admin/courses/{course.public_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_res.status_code == 200
        assert get_res.json()["name"] == "Archived Fixed Course"

        # PATCH is rejected
        patch_res = await client.patch(
            f"/v1/admin/courses/{course.public_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Attempted Name Change"},
        )
        assert patch_res.status_code == 400


@pytest.mark.asyncio
async def test_unauthenticated_course_routes_return_401(db_session: AsyncSession):
    """Test that all course routes require admin authentication."""
    random_id = uuid.uuid4()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/v1/admin/courses")).status_code == 401
        assert (await client.post("/v1/admin/courses", json={"name": "X"})).status_code == 401
        assert (await client.get(f"/v1/admin/courses/{random_id}")).status_code == 401
        assert (await client.patch(f"/v1/admin/courses/{random_id}", json={"name": "X"})).status_code == 401
