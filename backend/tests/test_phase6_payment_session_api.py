"""Automated integration and unit test suite for Phase 6 — UPI Payment Session + QR."""

import urllib.parse
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rate_limiter import auth_rate_limiter
from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.batch import Batch
from app.models.course import Course
from app.models.payment_session import PaymentSession
from app.models.payment_submission import PaymentSubmission
from app.services.upi_service import build_upi_uri, generate_reference_id


@pytest.fixture(autouse=True)
def setup_test_environment(db_session: AsyncSession):
    """Reset rate limiter and override database dependency for each test."""
    auth_rate_limiter.reset()
    app.dependency_overrides[get_db] = lambda: db_session
    yield
    auth_rate_limiter.reset()
    app.dependency_overrides.clear()


@pytest.fixture
async def active_course_and_batch(db_session: AsyncSession):
    """Create an active course and active batch."""
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
async def test_create_payment_session_success(active_course_and_batch):
    """Verify POST /v1/public/payment-sessions creates a session with PENDING status and snapshots."""
    course, batch = active_course_and_batch

    payload = {
        "batch_public_id": str(batch.public_id),
        "full_name": "Anand J Nair",
        "phone": "+91 98765 43210",
        "email": "anand@example.com",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/public/payment-sessions", json=payload)

    assert resp.status_code == 201
    data = resp.json()

    assert data["public_id"] is not None
    assert data["full_name"] == "Anand J Nair"
    assert data["phone"] == "9876543210"
    assert data["email"] == "anand@example.com"
    assert data["course_name"] == course.name
    assert data["batch_name"] == batch.name
    assert data["amount_inr"] == 3500
    assert data["status"] == "PENDING"
    assert data["reference_id"].startswith("ANAND_3210_")
    assert data["upi_id"] == settings.UPI_ID
    assert data["payee_name"] == settings.UPI_PAYEE_NAME
    assert "upi://pay" in data["upi_uri"]
    assert "id" not in data
    assert "course_id" not in data
    assert "batch_id" not in data


@pytest.mark.asyncio
async def test_payment_session_defaults_to_pending(active_course_and_batch):
    """Verify payment session initial status is strictly PENDING."""
    _, batch = active_course_and_batch

    payload = {
        "batch_public_id": str(batch.public_id),
        "full_name": "Test User",
        "phone": "9876543210",
        "email": "user@example.com",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/public/payment-sessions", json=payload)

    assert resp.status_code == 201
    assert resp.json()["status"] == "PENDING"


@pytest.mark.asyncio
async def test_payment_session_uses_authoritative_batch_amount(active_course_and_batch):
    """Verify payment session fee is derived from the database batch.amount_inr."""
    _, batch = active_course_and_batch

    payload = {
        "batch_public_id": str(batch.public_id),
        "full_name": "Test User",
        "phone": "9876543210",
        "email": "user@example.com",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/public/payment-sessions", json=payload)

    assert resp.status_code == 201
    assert resp.json()["amount_inr"] == 3500


@pytest.mark.asyncio
async def test_client_amount_cannot_override_batch_amount(active_course_and_batch):
    """Verify client attempt to supply amount_inr is rejected with 422."""
    _, batch = active_course_and_batch

    tampered = {
        "batch_public_id": str(batch.public_id),
        "full_name": "Test User",
        "phone": "9876543210",
        "email": "user@example.com",
        "amount_inr": 1,  # Injected amount
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/public/payment-sessions", json=tampered)

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_client_upi_id_cannot_override_server_configuration(active_course_and_batch):
    """Verify client cannot inject upi_id or payee_name."""
    _, batch = active_course_and_batch

    tampered = {
        "batch_public_id": str(batch.public_id),
        "full_name": "Test User",
        "phone": "9876543210",
        "email": "user@example.com",
        "upi_id": "hacker@upi",
        "payee_name": "Fake Payee",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/public/payment-sessions", json=tampered)

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_client_reference_id_cannot_override_generated_reference(active_course_and_batch):
    """Verify client cannot inject reference_id."""
    _, batch = active_course_and_batch

    tampered = {
        "batch_public_id": str(batch.public_id),
        "full_name": "Test User",
        "phone": "9876543210",
        "email": "user@example.com",
        "reference_id": "CUSTOM_REF_123",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/public/payment-sessions", json=tampered)

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_payment_session_stores_all_immutable_snapshots(db_session: AsyncSession, active_course_and_batch):
    """Verify DB row stores all historical snapshots accurately."""
    course, batch = active_course_and_batch

    payload = {
        "batch_public_id": str(batch.public_id),
        "full_name": "Pooja Sharma",
        "phone": "9876543210",
        "email": "pooja@example.com",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/public/payment-sessions", json=payload)

    assert resp.status_code == 201
    public_id = uuid.UUID(resp.json()["public_id"])

    # Query directly from DB
    stmt = select(PaymentSession).where(PaymentSession.public_id == public_id)
    result = await db_session.execute(stmt)
    session_row = result.scalar_one()

    assert session_row.course_name_snapshot == course.name
    assert session_row.batch_name_snapshot == batch.name
    assert session_row.amount_inr == batch.amount_inr
    assert session_row.upi_id_snapshot == settings.UPI_ID
    assert session_row.payee_name_snapshot == settings.UPI_PAYEE_NAME
    assert session_row.upi_uri.startswith("upi://pay?")
    assert session_row.status == "PENDING"


@pytest.mark.asyncio
async def test_payment_session_reference_is_unique(active_course_and_batch):
    """Verify successive creations generate distinct, non-colliding reference IDs."""
    _, batch = active_course_and_batch

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp1 = await client.post(
            "/v1/public/payment-sessions",
            json={
                "batch_public_id": str(batch.public_id),
                "full_name": "Same Name",
                "phone": "9876543210",
                "email": "user1@example.com",
            },
        )
        resp2 = await client.post(
            "/v1/public/payment-sessions",
            json={
                "batch_public_id": str(batch.public_id),
                "full_name": "Same Name",
                "phone": "9876543210",
                "email": "user2@example.com",
            },
        )

    assert resp1.status_code == 201
    assert resp2.status_code == 201
    ref1 = resp1.json()["reference_id"]
    ref2 = resp2.json()["reference_id"]
    assert ref1 != ref2


@pytest.mark.asyncio
async def test_invalid_batch_returns_404():
    """Verify non-existent batch UUID returns 404."""
    random_id = uuid.uuid4()
    payload = {
        "batch_public_id": str(random_id),
        "full_name": "Test User",
        "phone": "9876543210",
        "email": "user@example.com",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/public/payment-sessions", json=payload)

    assert resp.status_code == 404
    assert resp.json()["detail"] == "This registration link is no longer available."


@pytest.mark.asyncio
async def test_inactive_or_archived_batch_returns_404(db_session: AsyncSession, active_course_and_batch):
    """Verify inactive and archived batches return 404."""
    course, batch = active_course_and_batch

    # Inactive
    batch.status = "INACTIVE"
    await db_session.flush()

    payload = {
        "batch_public_id": str(batch.public_id),
        "full_name": "Test User",
        "phone": "9876543210",
        "email": "user@example.com",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp_inactive = await client.post("/v1/public/payment-sessions", json=payload)

    assert resp_inactive.status_code == 404

    # Archived
    batch.status = "ARCHIVED"
    await db_session.flush()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp_archived = await client.post("/v1/public/payment-sessions", json=payload)

    assert resp_archived.status_code == 404


@pytest.mark.asyncio
async def test_inactive_or_archived_course_returns_404(db_session: AsyncSession, active_course_and_batch):
    """Verify active batch under inactive or archived parent course returns 404."""
    course, batch = active_course_and_batch

    # Inactive Course
    course.status = "INACTIVE"
    await db_session.flush()

    payload = {
        "batch_public_id": str(batch.public_id),
        "full_name": "Test User",
        "phone": "9876543210",
        "email": "user@example.com",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp_inactive = await client.post("/v1/public/payment-sessions", json=payload)

    assert resp_inactive.status_code == 404


@pytest.mark.asyncio
async def test_invalid_participant_data_rejected(active_course_and_batch):
    """Verify phone, email, and name validations."""
    _, batch = active_course_and_batch

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid phone
        resp_phone = await client.post(
            "/v1/public/payment-sessions",
            json={
                "batch_public_id": str(batch.public_id),
                "full_name": "Test User",
                "phone": "12345",
                "email": "user@example.com",
            },
        )
        assert resp_phone.status_code == 422

        # Invalid email
        resp_email = await client.post(
            "/v1/public/payment-sessions",
            json={
                "batch_public_id": str(batch.public_id),
                "full_name": "Test User",
                "phone": "9876543210",
                "email": "not-an-email",
            },
        )
        assert resp_email.status_code == 422


@pytest.mark.asyncio
async def test_upi_uri_exact_semantics_and_url_encoding():
    """Verify URI structure, URL encoding, and query parameters."""
    ref = "ANAND_4321_X9Y2"
    uri = build_upi_uri(
        upi_id="merchant@bank",
        payee_name="Samagra Training & Tech",
        amount_inr=5000,
        reference_id=ref,
    )

    assert uri.startswith("upi://pay?")
    parsed = urllib.parse.urlparse(uri)
    qs = urllib.parse.parse_qs(parsed.query)

    assert qs["pa"][0] == "merchant@bank"
    assert qs["pn"][0] == "Samagra Training & Tech"
    assert qs["am"][0] == "5000"
    assert qs["cu"][0] == "INR"
    assert qs["tn"][0] == ref
    assert qs["tr"][0] == ref


@pytest.mark.asyncio
async def test_payment_session_snapshots_immutable_on_batch_updates(db_session: AsyncSession, active_course_and_batch):
    """Verify that updating course/batch names and amounts does NOT alter historical PaymentSession snapshots."""
    course, batch = active_course_and_batch

    payload = {
        "batch_public_id": str(batch.public_id),
        "full_name": "Immutable User",
        "phone": "9876543210",
        "email": "immutable@example.com",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/public/payment-sessions", json=payload)

    assert resp.status_code == 201
    session_pub_id = uuid.UUID(resp.json()["public_id"])

    # Admin updates Course name, Batch name, and Amount
    course.name = "Renamed Course 2027"
    batch.name = "Cohort October 2027"
    batch.amount_inr = 9999
    await db_session.flush()

    # Re-fetch payment session
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        get_resp = await client.get(f"/v1/public/payment-sessions/{session_pub_id}")

    assert get_resp.status_code == 200
    data = get_resp.json()

    # Snapshots MUST remain original
    assert data["course_name"] == "AI & Cloud Architectures"
    assert data["batch_name"] == "September 2026 Cohort"
    assert data["amount_inr"] == 3500


@pytest.mark.asyncio
async def test_public_payment_session_lookup_success_and_read_only(active_course_and_batch):
    """Verify GET /v1/public/payment-sessions/{public_id} resolves session without altering status."""
    _, batch = active_course_and_batch

    payload = {
        "batch_public_id": str(batch.public_id),
        "full_name": "Lookup User",
        "phone": "9876543210",
        "email": "lookup@example.com",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/v1/public/payment-sessions", json=payload)
        assert create_resp.status_code == 201
        session_pub_id = create_resp.json()["public_id"]

        get_resp = await client.get(f"/v1/public/payment-sessions/{session_pub_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()

        assert data["public_id"] == session_pub_id
        assert data["status"] == "PENDING"
        assert data["amount_inr"] == 3500
        assert "id" not in data
        assert "course_id" not in data


@pytest.mark.asyncio
async def test_public_payment_session_unknown_id_404():
    """Verify random UUID returns 404."""
    random_id = uuid.uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/v1/public/payment-sessions/{random_id}")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "This payment session is no longer available."


@pytest.mark.asyncio
async def test_phase6_boundary_no_payment_submission(db_session: AsyncSession, active_course_and_batch):
    """Verify Phase 6 does NOT create any PaymentSubmission rows."""
    _, batch = active_course_and_batch

    payload = {
        "batch_public_id": str(batch.public_id),
        "full_name": "Boundary User",
        "phone": "9876543210",
        "email": "boundary@example.com",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/public/payment-sessions", json=payload)

    assert resp.status_code == 201
    created_pub_id = uuid.UUID(resp.json()["public_id"])

    # Query the created session and verify zero linked submissions
    stmt_session = select(PaymentSession).where(PaymentSession.public_id == created_pub_id)
    session_res = await db_session.execute(stmt_session)
    session_row = session_res.scalar_one()

    stmt = select(PaymentSubmission).where(PaymentSubmission.payment_session_id == session_row.id)
    res = await db_session.execute(stmt)
    submissions = res.scalars().all()
    assert len(submissions) == 0
    assert session_row.status == "PENDING"


@pytest.mark.asyncio
async def test_payment_session_expiration_behavior(db_session: AsyncSession, active_course_and_batch):
    """Verify that an expired session returns is_expired=True and status=EXPIRED."""
    course, batch = active_course_and_batch

    now_utc = datetime.now(timezone.utc)
    expired_session = PaymentSession(
        full_name="Expired User",
        phone="9876543210",
        email="expired@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot=course.name,
        batch_name_snapshot=batch.name,
        amount_inr=batch.amount_inr,
        reference_id=f"REF_EXP_{uuid.uuid4().hex[:6].upper()}",
        upi_id_snapshot=settings.UPI_ID,
        payee_name_snapshot=settings.UPI_PAYEE_NAME,
        upi_uri="upi://pay?pa=test@upi",
        status="PENDING",
        expires_at=now_utc - timedelta(minutes=5),  # Expired 5 minutes ago
    )
    db_session.add(expired_session)
    await db_session.flush()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/v1/public/payment-sessions/{expired_session.public_id}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["is_expired"] is True
    assert data["status"] == "EXPIRED"
