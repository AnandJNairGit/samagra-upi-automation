"""Integration tests for Admin Batch Management APIs."""

import uuid
from datetime import datetime, timezone
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
from app.models.payment_session import PaymentSession


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
        full_name="Batch Test Admin",
        is_active=True,
    )
    db.add(admin)
    await db.flush()
    token = create_access_token(admin.public_id)
    return admin, token


@pytest.mark.asyncio
async def test_create_batch_success_default_active(db_session: AsyncSession):
    """Test POST /v1/admin/batches creates a batch under a course with default status ACTIVE."""
    _, token = await create_test_admin(db_session)
    course = Course(public_id=uuid.uuid4(), name="Python Automation", status="ACTIVE")
    db_session.add(course)
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/admin/batches",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "course_public_id": str(course.public_id),
                "name": "September 2026 Cohort",
                "amount_inr": 2500,
                "starts_at": "2026-09-01T00:00:00Z",
                "ends_at": "2026-09-30T00:00:00Z",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "September 2026 Cohort"
        assert data["amount_inr"] == 2500
        assert data["status"] == "ACTIVE"
        assert data["course_public_id"] == str(course.public_id)
        assert data["course_name"] == "Python Automation"


@pytest.mark.asyncio
async def test_create_batch_explicit_inactive_success(db_session: AsyncSession):
    """Test POST /v1/admin/batches allows explicit INACTIVE status."""
    _, token = await create_test_admin(db_session)
    course = Course(public_id=uuid.uuid4(), name="Web Dev", status="ACTIVE")
    db_session.add(course)
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/admin/batches",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "course_public_id": str(course.public_id),
                "name": "Unpublished Cohort",
                "amount_inr": 1500,
                "status": "INACTIVE",
            },
        )
        assert response.status_code == 201
        assert response.json()["status"] == "INACTIVE"


@pytest.mark.asyncio
async def test_create_batch_archived_status_rejected(db_session: AsyncSession):
    """Test POST /v1/admin/batches rejects ARCHIVED status on creation."""
    _, token = await create_test_admin(db_session)
    course = Course(public_id=uuid.uuid4(), name="Course", status="ACTIVE")
    db_session.add(course)
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/admin/batches",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "course_public_id": str(course.public_id),
                "name": "Archived Batch",
                "amount_inr": 1000,
                "status": "ARCHIVED",
            },
        )
        assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_create_batch_under_archived_course_rejected(db_session: AsyncSession):
    """Test POST /v1/admin/batches rejects creating a batch under an ARCHIVED course."""
    _, token = await create_test_admin(db_session)
    archived_course = Course(public_id=uuid.uuid4(), name="Archived Legacy Course", status="ARCHIVED")
    db_session.add(archived_course)
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/admin/batches",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "course_public_id": str(archived_course.public_id),
                "name": "Attempted Cohort",
                "amount_inr": 2000,
            },
        )
        assert response.status_code == 400
        assert "archived" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_batch_under_inactive_course_allowed(db_session: AsyncSession):
    """Test POST /v1/admin/batches permits creating an ACTIVE batch under an INACTIVE course."""
    _, token = await create_test_admin(db_session)
    inactive_course = Course(public_id=uuid.uuid4(), name="Inactive Parent Course", status="INACTIVE")
    db_session.add(inactive_course)
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/admin/batches",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "course_public_id": str(inactive_course.public_id),
                "name": "Active Cohort in Inactive Course",
                "amount_inr": 3000,
                "status": "ACTIVE",
            },
        )
        assert response.status_code == 201
        assert response.json()["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_create_batch_amount_zero_or_negative_rejected(db_session: AsyncSession):
    """Test POST /v1/admin/batches rejects amount_inr <= 0."""
    _, token = await create_test_admin(db_session)
    course = Course(public_id=uuid.uuid4(), name="Free Course", status="ACTIVE")
    db_session.add(course)
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Zero amount
        res_zero = await client.post(
            "/v1/admin/batches",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "course_public_id": str(course.public_id),
                "name": "Zero Batch",
                "amount_inr": 0,
            },
        )
        assert res_zero.status_code == 422

        # Negative amount
        res_neg = await client.post(
            "/v1/admin/batches",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "course_public_id": str(course.public_id),
                "name": "Negative Batch",
                "amount_inr": -500,
            },
        )
        assert res_neg.status_code == 422


@pytest.mark.asyncio
async def test_create_batch_invalid_date_range_rejected(db_session: AsyncSession):
    """Test POST /v1/admin/batches rejects ends_at < starts_at."""
    _, token = await create_test_admin(db_session)
    course = Course(public_id=uuid.uuid4(), name="Date Course", status="ACTIVE")
    db_session.add(course)
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/admin/batches",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "course_public_id": str(course.public_id),
                "name": "Invalid Date Batch",
                "amount_inr": 1000,
                "starts_at": "2026-09-30T00:00:00Z",
                "ends_at": "2026-09-01T00:00:00Z",
            },
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_batches_filter_by_course_and_status(db_session: AsyncSession):
    """Test GET /v1/admin/batches filtering by course_public_id and status."""
    _, token = await create_test_admin(db_session)

    c1 = Course(public_id=uuid.uuid4(), name="Course A", status="ACTIVE")
    c2 = Course(public_id=uuid.uuid4(), name="Course B", status="ACTIVE")
    db_session.add_all([c1, c2])
    await db_session.flush()

    b1 = Batch(public_id=uuid.uuid4(), course_id=c1.id, name="Cohort A1", amount_inr=1000, status="ACTIVE")
    b2 = Batch(public_id=uuid.uuid4(), course_id=c1.id, name="Cohort A2", amount_inr=1000, status="INACTIVE")
    b3 = Batch(public_id=uuid.uuid4(), course_id=c2.id, name="Cohort B1", amount_inr=2000, status="ACTIVE")
    db_session.add_all([b1, b2, b3])
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Filter by course_public_id
        res_course = await client.get(
            f"/v1/admin/batches?course_public_id={c1.public_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_course.status_code == 200
        data_c = res_course.json()
        assert len(data_c) == 2
        assert all(b["course_public_id"] == str(c1.public_id) for b in data_c)

        # Filter by course and status
        res_both = await client.get(
            f"/v1/admin/batches?course_public_id={c1.public_id}&status=ACTIVE",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_both.status_code == 200
        data_b = res_both.json()
        assert len(data_b) == 1
        assert data_b[0]["public_id"] == str(b1.public_id)


@pytest.mark.asyncio
async def test_update_batch_amount_and_dates(db_session: AsyncSession):
    """Test PATCH /v1/admin/batches/{id} updates amount and dates."""
    _, token = await create_test_admin(db_session)
    course = Course(public_id=uuid.uuid4(), name="Course", status="ACTIVE")
    db_session.add(course)
    await db_session.flush()

    batch = Batch(public_id=uuid.uuid4(), course_id=course.id, name="Old Batch", amount_inr=1000, status="ACTIVE")
    db_session.add(batch)
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            f"/v1/admin/batches/{batch.public_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "Updated Batch Name",
                "amount_inr": 2000,
                "starts_at": "2026-10-01T00:00:00Z",
                "ends_at": "2026-10-31T00:00:00Z",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Batch Name"
        assert data["amount_inr"] == 2000


@pytest.mark.asyncio
async def test_batch_lifecycle_active_to_inactive_to_archived(db_session: AsyncSession):
    """Test full allowed batch lifecycle transitions."""
    _, token = await create_test_admin(db_session)
    course = Course(public_id=uuid.uuid4(), name="Course", status="ACTIVE")
    db_session.add(course)
    await db_session.flush()

    batch = Batch(public_id=uuid.uuid4(), course_id=course.id, name="Lifecycle Batch", amount_inr=1000, status="ACTIVE")
    db_session.add(batch)
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # ACTIVE -> INACTIVE
        r1 = await client.patch(
            f"/v1/admin/batches/{batch.public_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": "INACTIVE"},
        )
        assert r1.status_code == 200
        assert r1.json()["status"] == "INACTIVE"

        # INACTIVE -> ACTIVE
        r2 = await client.patch(
            f"/v1/admin/batches/{batch.public_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": "ACTIVE"},
        )
        assert r2.status_code == 200
        assert r2.json()["status"] == "ACTIVE"

        # ACTIVE -> ARCHIVED
        r3 = await client.patch(
            f"/v1/admin/batches/{batch.public_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": "ARCHIVED"},
        )
        assert r3.status_code == 200
        assert r3.json()["status"] == "ARCHIVED"


@pytest.mark.asyncio
async def test_batch_archived_is_terminal_and_readonly(db_session: AsyncSession):
    """Test that an ARCHIVED batch cannot be reactivated or mutated."""
    _, token = await create_test_admin(db_session)
    course = Course(public_id=uuid.uuid4(), name="Course", status="ACTIVE")
    db_session.add(course)
    await db_session.flush()

    batch = Batch(public_id=uuid.uuid4(), course_id=course.id, name="Archived Batch", amount_inr=1000, status="ARCHIVED")
    db_session.add(batch)
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Reactivation attempt -> 400
        r_reactivate = await client.patch(
            f"/v1/admin/batches/{batch.public_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"status": "ACTIVE"},
        )
        assert r_reactivate.status_code == 400

        # Mutation attempt -> 400
        r_mutate = await client.patch(
            f"/v1/admin/batches/{batch.public_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"amount_inr": 5000},
        )
        assert r_mutate.status_code == 400


@pytest.mark.asyncio
async def test_batch_reassign_course_allowed_when_no_payment_sessions(db_session: AsyncSession):
    """Test reassigning batch to another active course when 0 payment sessions exist."""
    _, token = await create_test_admin(db_session)
    c1 = Course(public_id=uuid.uuid4(), name="Course 1", status="ACTIVE")
    c2 = Course(public_id=uuid.uuid4(), name="Course 2", status="ACTIVE")
    db_session.add_all([c1, c2])
    await db_session.flush()

    batch = Batch(public_id=uuid.uuid4(), course_id=c1.id, name="Reassign Batch", amount_inr=1000, status="ACTIVE")
    db_session.add(batch)
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            f"/v1/admin/batches/{batch.public_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"course_public_id": str(c2.public_id)},
        )
        assert response.status_code == 200
        assert response.json()["course_public_id"] == str(c2.public_id)
        assert response.json()["course_name"] == "Course 2"


@pytest.mark.asyncio
async def test_batch_reassign_course_forbidden_when_payment_sessions_exist(db_session: AsyncSession):
    """Test reassigning batch course is forbidden when associated payment sessions exist."""
    _, token = await create_test_admin(db_session)
    c1 = Course(public_id=uuid.uuid4(), name="Original Course", status="ACTIVE")
    c2 = Course(public_id=uuid.uuid4(), name="Target Course", status="ACTIVE")
    db_session.add_all([c1, c2])
    await db_session.flush()

    batch = Batch(public_id=uuid.uuid4(), course_id=c1.id, name="Paid Batch", amount_inr=1000, status="ACTIVE")
    db_session.add(batch)
    await db_session.flush()

    # Create associated payment session
    session = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="Student",
        phone="+919876543210",
        email="student@example.com",
        course_id=c1.id,
        batch_id=batch.id,
        course_name_snapshot="Original Course",
        batch_name_snapshot="Paid Batch",
        amount_inr=1000,
        reference_id=f"REF_{uuid.uuid4().hex[:8].upper()}",
        upi_id_snapshot="upi@bank",
        payee_name_snapshot="Payee",
        upi_uri="upi://pay?pa=upi@bank",
        status="PENDING",
    )
    db_session.add(session)
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            f"/v1/admin/batches/{batch.public_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"course_public_id": str(c2.public_id)},
        )
        assert response.status_code == 400
        assert "payment sessions" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_batch_reassign_to_archived_course_rejected(db_session: AsyncSession):
    """Test reassigning batch to an ARCHIVED course is rejected."""
    _, token = await create_test_admin(db_session)
    c_active = Course(public_id=uuid.uuid4(), name="Active Course", status="ACTIVE")
    c_archived = Course(public_id=uuid.uuid4(), name="Archived Course", status="ARCHIVED")
    db_session.add_all([c_active, c_archived])
    await db_session.flush()

    batch = Batch(public_id=uuid.uuid4(), course_id=c_active.id, name="Test Batch", amount_inr=1000, status="ACTIVE")
    db_session.add(batch)
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            f"/v1/admin/batches/{batch.public_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"course_public_id": str(c_archived.public_id)},
        )
        assert response.status_code == 400
        assert "archived" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_unauthenticated_batch_routes_return_401(db_session: AsyncSession):
    """Test that all batch routes require admin authorization."""
    random_id = uuid.uuid4()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/v1/admin/batches")).status_code == 401
        assert (await client.post("/v1/admin/batches", json={"name": "X"})).status_code == 401
        assert (await client.get(f"/v1/admin/batches/{random_id}")).status_code == 401
        assert (await client.patch(f"/v1/admin/batches/{random_id}", json={"name": "X"})).status_code == 401
