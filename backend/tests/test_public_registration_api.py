"""Automated test suite for Phase 5 Public Registration API."""

import uuid
from datetime import datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.auth.rate_limiter import auth_rate_limiter
from app.main import app
from app.models.batch import Batch
from app.models.course import Course
from app.models.payment_session import PaymentSession


@pytest.fixture(autouse=True)
def setup_test_environment(db_session: AsyncSession):
    """Reset in-memory rate limiter and override get_db dependency before each test."""
    auth_rate_limiter.reset()
    app.dependency_overrides[get_db] = lambda: db_session
    yield
    auth_rate_limiter.reset()
    app.dependency_overrides.clear()


@pytest.fixture
async def active_course_and_batch(db_session: AsyncSession):
    """Fixture creating an ACTIVE Course and an ACTIVE Batch."""
    now_utc = datetime.now(timezone.utc)
    course = Course(
        name="AI & Cloud Architectures",
        description="Comprehensive masterclass.",
        status="ACTIVE",
        created_at=now_utc,
        updated_at=now_utc,
    )
    db_session.add(course)
    await db_session.flush()

    batch = Batch(
        course_id=course.id,
        name="September 2026 Cohort",
        amount_inr=3500,
        status="ACTIVE",
        starts_at=now_utc,
        ends_at=None,
        created_at=now_utc,
        updated_at=now_utc,
    )
    db_session.add(batch)
    await db_session.flush()
    await db_session.refresh(course)
    await db_session.refresh(batch)
    return course, batch


@pytest.mark.asyncio
async def test_public_active_batch_returns_200(active_course_and_batch):
    """Verify public batch lookup succeeds for ACTIVE batch under ACTIVE course."""
    course, batch = active_course_and_batch

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/v1/public/batches/{batch.public_id}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["public_id"] == str(batch.public_id)
    assert data["course_name"] == course.name
    assert data["batch_name"] == batch.name
    assert data["amount_inr"] == 3500
    assert "id" not in data
    assert "course_id" not in data
    assert "created_by" not in data


@pytest.mark.asyncio
async def test_public_inactive_batch_returns_404(db_session: AsyncSession, active_course_and_batch):
    """Verify public batch lookup returns generic 404 when batch is INACTIVE."""
    course, batch = active_course_and_batch
    batch.status = "INACTIVE"
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/v1/public/batches/{batch.public_id}")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "This registration link is no longer available."


@pytest.mark.asyncio
async def test_public_archived_batch_returns_404(db_session: AsyncSession, active_course_and_batch):
    """Verify public batch lookup returns generic 404 when batch is ARCHIVED."""
    course, batch = active_course_and_batch
    batch.status = "ARCHIVED"
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/v1/public/batches/{batch.public_id}")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "This registration link is no longer available."


@pytest.mark.asyncio
async def test_public_batch_under_inactive_course_returns_404(db_session: AsyncSession, active_course_and_batch):
    """Verify public batch lookup returns 404 when parent course is INACTIVE."""
    course, batch = active_course_and_batch
    course.status = "INACTIVE"
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/v1/public/batches/{batch.public_id}")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "This registration link is no longer available."


@pytest.mark.asyncio
async def test_public_batch_under_archived_course_returns_404(db_session: AsyncSession, active_course_and_batch):
    """Verify public batch lookup returns 404 when parent course is ARCHIVED."""
    course, batch = active_course_and_batch
    course.status = "ARCHIVED"
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/v1/public/batches/{batch.public_id}")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "This registration link is no longer available."


@pytest.mark.asyncio
async def test_nonexistent_public_batch_returns_404():
    """Verify public lookup for random UUID returns generic 404."""
    random_id = uuid.uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/v1/public/batches/{random_id}")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "This registration link is no longer available."


@pytest.mark.asyncio
async def test_public_endpoint_requires_no_admin_auth(active_course_and_batch):
    """Verify public endpoint is accessible without Authorization header."""
    _, batch = active_course_and_batch
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/v1/public/batches/{batch.public_id}")

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_endpoints_remain_protected(active_course_and_batch):
    """Verify admin endpoints return 401 when accessed unauthenticated."""
    _, batch = active_course_and_batch
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp_courses = await client.get("/v1/admin/courses")
        resp_batches = await client.get("/v1/admin/batches")
        resp_single_batch = await client.get(f"/v1/admin/batches/{batch.public_id}")

    assert resp_courses.status_code == 401
    assert resp_batches.status_code == 401
    assert resp_single_batch.status_code == 401


@pytest.mark.asyncio
async def test_public_validation_endpoint_success(active_course_and_batch):
    """Verify participant registration validation returns authoritative context."""
    course, batch = active_course_and_batch

    payload = {
        "batch_public_id": str(batch.public_id),
        "full_name": "Rohan Sharma",
        "phone": "+91 98765 43210",
        "email": "rohan@example.com",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/public/register/validate", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["batch_public_id"] == str(batch.public_id)
    assert data["course_name"] == course.name
    assert data["batch_name"] == batch.name
    assert data["amount_inr"] == 3500
    assert data["full_name"] == "Rohan Sharma"
    assert data["phone"] == "9876543210"  # Normalized Indian phone
    assert data["email"] == "rohan@example.com"


@pytest.mark.asyncio
async def test_public_validation_does_not_create_payment_session(db_session: AsyncSession, active_course_and_batch):
    """Verify Phase 5 validation endpoint does NOT insert any payment session in the database."""
    _, batch = active_course_and_batch

    payload = {
        "batch_public_id": str(batch.public_id),
        "full_name": "Participant Test",
        "phone": "9876543210",
        "email": "participant@example.com",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/public/register/validate", json=payload)

    assert resp.status_code == 200

    # Query payment_sessions table to verify zero records exist
    stmt = select(PaymentSession).where(PaymentSession.batch_id == batch.id)
    result = await db_session.execute(stmt)
    sessions = result.scalars().all()
    assert len(sessions) == 0


@pytest.mark.asyncio
async def test_public_validation_forbids_client_amount_tampering(active_course_and_batch):
    """Verify client cannot supply amount_inr or course fields (extra='forbid')."""
    _, batch = active_course_and_batch

    tampered_payload = {
        "batch_public_id": str(batch.public_id),
        "full_name": "Tamper Test",
        "phone": "9876543210",
        "email": "tamper@example.com",
        "amount_inr": 1,  # Attempt to override fee
        "course_name": "Fake Course",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/public/register/validate", json=tampered_payload)

    # Pydantic extra='forbid' raises 422 Unprocessable Entity
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_public_validation_invalid_phone_rejected(active_course_and_batch):
    """Verify non-Indian or malformed phone numbers are rejected with 422."""
    _, batch = active_course_and_batch

    invalid_phones = ["12345", "5876543210", "987654321012", "abcdefghij"]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for ph in invalid_phones:
            payload = {
                "batch_public_id": str(batch.public_id),
                "full_name": "Phone Test",
                "phone": ph,
                "email": "test@example.com",
            }
            resp = await client.post("/v1/public/register/validate", json=payload)
            assert resp.status_code == 422


@pytest.mark.asyncio
async def test_public_validation_invalid_email_rejected(active_course_and_batch):
    """Verify malformed email addresses are rejected with 422."""
    _, batch = active_course_and_batch

    invalid_emails = ["not-an-email", "@missinguser.com", "user@"]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for em in invalid_emails:
            payload = {
                "batch_public_id": str(batch.public_id),
                "full_name": "Email Test",
                "phone": "9876543210",
                "email": em,
            }
            resp = await client.post("/v1/public/register/validate", json=payload)
            assert resp.status_code == 422


@pytest.mark.asyncio
async def test_public_validation_short_or_whitespace_name_rejected(active_course_and_batch):
    """Verify empty or 1-character names are rejected with 422."""
    _, batch = active_course_and_batch

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "batch_public_id": str(batch.public_id),
            "full_name": "   ",
            "phone": "9876543210",
            "email": "test@example.com",
        }
        resp = await client.post("/v1/public/register/validate", json=payload)
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_public_rate_limiting(active_course_and_batch):
    """Verify rate limiter protects public lookup from flood abuse (max 60/min)."""
    _, batch = active_course_and_batch

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(60):
            r = await client.get(f"/v1/public/batches/{batch.public_id}")
            assert r.status_code == 200

        # 61st request should be rate-limited
        r_blocked = await client.get(f"/v1/public/batches/{batch.public_id}")
        assert r_blocked.status_code == 429
        assert "Retry-After" in r_blocked.headers
