"""Integration and concurrency test suite for Phase 7 UTR submission & WhatsApp notification."""

import asyncio
import re
import urllib.parse
import uuid
from datetime import datetime, timedelta, timezone
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.auth.rate_limiter import auth_rate_limiter
from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.batch import Batch
from app.models.course import Course
from app.models.payment_session import PaymentSession
from app.models.payment_submission import PaymentSubmission
from app.services.exceptions import DuplicateUTRError
from app.services.payment_submission_service import PaymentSubmissionService
from app.services.whatsapp_service import mask_utr


@pytest.fixture(autouse=True)
def setup_test_environment(db_session: AsyncSession):
    """Reset rate limiter and override database dependency for each test."""
    auth_rate_limiter.reset()
    app.dependency_overrides[get_db] = lambda: db_session
    yield
    auth_rate_limiter.reset()
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client():
    """Async HTTP client fixture with ASGI transport."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def active_cohort(db_session: AsyncSession):
    """Fixture providing an active course and active cohort."""
    course = Course(
        public_id=uuid.uuid4(),
        name="Full Stack Python Mastery",
        description="Comprehensive backend and cloud deployment course",
        status="ACTIVE",
    )
    db_session.add(course)
    await db_session.flush()

    batch = Batch(
        public_id=uuid.uuid4(),
        course_id=course.id,
        name="August 2026 Cohort",
        amount_inr=2500,
        status="ACTIVE",
        starts_at=datetime.now(timezone.utc),
        ends_at=datetime.now(timezone.utc) + timedelta(days=60),
    )
    db_session.add(batch)
    await db_session.flush()
    return course, batch


@pytest.fixture
async def pending_payment_session(db_session: AsyncSession, active_cohort):
    """Fixture providing an active PENDING PaymentSession."""
    course, batch = active_cohort
    session = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="Aditya Nair",
        phone="9876543210",
        email="aditya.nair@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot=course.name,
        batch_name_snapshot=batch.name,
        amount_inr=batch.amount_inr,
        reference_id=f"ADITYA_3210_{uuid.uuid4().hex[:4].upper()}",
        upi_id_snapshot="samagralearning@ibl",
        payee_name_snapshot="Samagra Training",
        upi_uri="upi://pay?pa=samagralearning@ibl&pn=Samagra%20Training&am=2500&cu=INR&tn=REF&tr=REF",
        status="PENDING",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    db_session.add(session)
    await db_session.flush()
    return session


# =============================================================================
# 1. FUNCTIONAL TESTS — PUBLIC UTR SUBMISSION ENDPOINT
# =============================================================================


@pytest.mark.asyncio
async def test_submit_valid_utr_success(client: AsyncClient, pending_payment_session: PaymentSession):
    """Test successful UTR submission returns 201 with masked UTR, SUBMITTED status, and WhatsApp URL."""
    utr_val = f"UTR{uuid.uuid4().hex[:9].upper()}"
    url = f"/v1/public/payment-sessions/{pending_payment_session.public_id}/submissions"

    response = await client.post(url, json={"utr": utr_val})

    assert response.status_code == 201
    data = response.json()

    assert data["payment_session_public_id"] == str(pending_payment_session.public_id)
    assert data["status"] == "SUBMITTED"
    assert "submission_public_id" in data
    assert data["utr_masked"] == mask_utr(utr_val)
    assert "submitted_at" in data

    # Verify WhatsApp deep link is populated
    assert "whatsapp_url" in data
    assert data["whatsapp_url"].startswith("https://wa.me/")
    assert settings.ADMIN_WHATSAPP_NUMBER in data["whatsapp_url"]


@pytest.mark.asyncio
async def test_payment_session_changes_pending_to_submitted(
    client: AsyncClient,
    db_session: AsyncSession,
    pending_payment_session: PaymentSession,
):
    """Test that UTR submission synchronizes PaymentSession and PaymentSubmission to SUBMITTED."""
    utr_val = f"UTR_SYNC_{uuid.uuid4().hex[:8].upper()}"
    url = f"/v1/public/payment-sessions/{pending_payment_session.public_id}/submissions"

    res = await client.post(url, json={"utr": utr_val})
    assert res.status_code == 201

    # Inspect database state
    ps_stmt = select(PaymentSession).where(PaymentSession.id == pending_payment_session.id)
    updated_ps = (await db_session.execute(ps_stmt)).scalar_one()
    assert updated_ps.status == "SUBMITTED"

    sub_stmt = select(PaymentSubmission).where(PaymentSubmission.payment_session_id == pending_payment_session.id)
    submission = (await db_session.execute(sub_stmt)).scalar_one()

    assert submission.status == "SUBMITTED"
    assert submission.utr == utr_val
    assert submission.is_current is True
    assert submission.reviewed_by is None
    assert submission.reviewed_at is None


@pytest.mark.asyncio
async def test_submitted_at_is_server_generated(
    client: AsyncClient,
    db_session: AsyncSession,
    pending_payment_session: PaymentSession,
):
    """Test that submitted_at timestamp is generated server-side in UTC."""
    before_submit = datetime.now(timezone.utc) - timedelta(seconds=2)
    utr_val = f"UTR_TIME_{uuid.uuid4().hex[:8].upper()}"
    url = f"/v1/public/payment-sessions/{pending_payment_session.public_id}/submissions"

    res = await client.post(url, json={"utr": utr_val})
    assert res.status_code == 201
    after_submit = datetime.now(timezone.utc) + timedelta(seconds=2)

    sub_stmt = select(PaymentSubmission).where(PaymentSubmission.payment_session_id == pending_payment_session.id)
    submission = (await db_session.execute(sub_stmt)).scalar_one()

    assert submission.submitted_at >= before_submit
    assert submission.submitted_at <= after_submit


@pytest.mark.asyncio
async def test_empty_or_whitespace_utr_rejected(
    client: AsyncClient,
    pending_payment_session: PaymentSession,
):
    """Test that empty or whitespace-only UTR is rejected with 422."""
    url = f"/v1/public/payment-sessions/{pending_payment_session.public_id}/submissions"

    # Blank string
    res1 = await client.post(url, json={"utr": ""})
    assert res1.status_code == 422

    # Whitespace only
    res2 = await client.post(url, json={"utr": "     "})
    assert res2.status_code == 422


@pytest.mark.asyncio
async def test_short_and_oversized_utr_rejected(
    client: AsyncClient,
    pending_payment_session: PaymentSession,
):
    """Test that UTR with length < 4 or > 100 characters is rejected with 422."""
    url = f"/v1/public/payment-sessions/{pending_payment_session.public_id}/submissions"

    # Too short (< 4 chars)
    res_short = await client.post(url, json={"utr": "123"})
    assert res_short.status_code == 422

    # Too long (> 100 chars)
    res_long = await client.post(url, json={"utr": "U" * 101})
    assert res_long.status_code == 422


@pytest.mark.asyncio
async def test_duplicate_utr_across_sessions_rejected_409(
    client: AsyncClient,
    db_session: AsyncSession,
    active_cohort,
):
    """Test that submitting an already used UTR across different payment sessions returns 409 Conflict."""
    course, batch = active_cohort

    # Create Session 1 & Session 2
    ps1 = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="User One",
        phone="9876543210",
        email="u1@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot=course.name,
        batch_name_snapshot=batch.name,
        amount_inr=2500,
        reference_id=f"U1_{uuid.uuid4().hex[:6].upper()}",
        upi_id_snapshot="samagra@upi",
        payee_name_snapshot="Samagra",
        upi_uri="upi://pay",
        status="PENDING",
    )
    ps2 = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="User Two",
        phone="9876543212",
        email="u2@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot=course.name,
        batch_name_snapshot=batch.name,
        amount_inr=2500,
        reference_id=f"U2_{uuid.uuid4().hex[:6].upper()}",
        upi_id_snapshot="samagra@upi",
        payee_name_snapshot="Samagra",
        upi_uri="upi://pay",
        status="PENDING",
    )
    db_session.add_all([ps1, ps2])
    await db_session.flush()

    shared_utr = f"UTR_SHARED_{uuid.uuid4().hex[:8].upper()}"

    # First submission succeeds (201)
    res1 = await client.post(f"/v1/public/payment-sessions/{ps1.public_id}/submissions", json={"utr": shared_utr})
    assert res1.status_code == 201

    # Second submission with same UTR returns 409 Conflict
    res2 = await client.post(f"/v1/public/payment-sessions/{ps2.public_id}/submissions", json={"utr": shared_utr})
    assert res2.status_code == 409
    assert "already been submitted" in res2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_already_submitted_session_rejects_resubmission_409(
    client: AsyncClient,
    pending_payment_session: PaymentSession,
):
    """Test that a payment session already in SUBMITTED status rejects subsequent submissions with 409."""
    url = f"/v1/public/payment-sessions/{pending_payment_session.public_id}/submissions"

    # Initial submission
    res1 = await client.post(url, json={"utr": f"UTR_A_{uuid.uuid4().hex[:8]}"})
    assert res1.status_code == 201

    # Resubmission attempt
    res2 = await client.post(url, json={"utr": f"UTR_B_{uuid.uuid4().hex[:8]}"})
    assert res2.status_code == 409
    assert "already been submitted" in res2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_nonexistent_payment_session_returns_404(client: AsyncClient):
    """Test that submitting UTR to a nonexistent session UUID returns 404 Not Found."""
    fake_uuid = uuid.uuid4()
    url = f"/v1/public/payment-sessions/{fake_uuid}/submissions"

    response = await client.post(url, json={"utr": "123456789012"})
    assert response.status_code == 404
    assert "available" in response.json()["detail"].lower() or "found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_expired_payment_session_rejects_utr(
    client: AsyncClient,
    db_session: AsyncSession,
    active_cohort,
):
    """Test that expired payment sessions reject UTR submissions with 400."""
    course, batch = active_cohort
    expired_session = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="Late User",
        phone="9876543210",
        email="late@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot=course.name,
        batch_name_snapshot=batch.name,
        amount_inr=batch.amount_inr,
        reference_id=f"LATE_{uuid.uuid4().hex[:6].upper()}",
        upi_id_snapshot="samagra@upi",
        payee_name_snapshot="Samagra",
        upi_uri="upi://pay",
        status="PENDING",
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),  # 5 minutes expired
    )
    db_session.add(expired_session)
    await db_session.flush()

    url = f"/v1/public/payment-sessions/{expired_session.public_id}/submissions"
    response = await client.post(url, json={"utr": "123456789012"})

    assert response.status_code == 400
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_financial_snapshots_remain_immutable(
    client: AsyncClient,
    db_session: AsyncSession,
    pending_payment_session: PaymentSession,
):
    """Test that UTR submission never mutates historical course, batch, or amount snapshots."""
    orig_course_snapshot = pending_payment_session.course_name_snapshot
    orig_batch_snapshot = pending_payment_session.batch_name_snapshot
    orig_amount = pending_payment_session.amount_inr
    orig_ref = pending_payment_session.reference_id
    orig_upi = pending_payment_session.upi_id_snapshot
    orig_uri = pending_payment_session.upi_uri

    url = f"/v1/public/payment-sessions/{pending_payment_session.public_id}/submissions"
    res = await client.post(url, json={"utr": f"UTR_{uuid.uuid4().hex[:8]}"})
    assert res.status_code == 201

    # Reload from DB
    await db_session.refresh(pending_payment_session)

    assert pending_payment_session.course_name_snapshot == orig_course_snapshot
    assert pending_payment_session.batch_name_snapshot == orig_batch_snapshot
    assert pending_payment_session.amount_inr == orig_amount
    assert pending_payment_session.reference_id == orig_ref
    assert pending_payment_session.upi_id_snapshot == orig_upi
    assert pending_payment_session.upi_uri == orig_uri


# =============================================================================
# 2. WHATSAPP NOTIFICATION TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_whatsapp_deep_link_format_and_encoding(
    client: AsyncClient,
    pending_payment_session: PaymentSession,
):
    """Test WhatsApp deep link construction, URL encoding, and message content."""
    utr_val = f"UTR_WA_{uuid.uuid4().hex[:8].upper()}"
    url = f"/v1/public/payment-sessions/{pending_payment_session.public_id}/submissions"

    response = await client.post(url, json={"utr": utr_val})
    assert response.status_code == 201
    data = response.json()

    wa_url = data["whatsapp_url"]
    assert wa_url.startswith(f"https://wa.me/{settings.ADMIN_WHATSAPP_NUMBER}?text=")

    # Extract and decode message parameter
    parsed_url = urllib.parse.urlparse(wa_url)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    decoded_message = query_params["text"][0]

    assert "NEW PAYMENT SUBMISSION" in decoded_message
    assert f"Name: {pending_payment_session.full_name}" in decoded_message
    assert f"Phone: {pending_payment_session.phone}" in decoded_message
    assert f"Email: {pending_payment_session.email}" in decoded_message
    assert f"Course: {pending_payment_session.course_name_snapshot}" in decoded_message
    assert f"Batch: {pending_payment_session.batch_name_snapshot}" in decoded_message
    assert f"Amount: ₹{pending_payment_session.amount_inr:,}" in decoded_message
    assert f"Reference ID: {pending_payment_session.reference_id}" in decoded_message
    assert f"UTR: {utr_val}" in decoded_message
    assert "Payment Status: SUBMITTED" in decoded_message


@pytest.mark.asyncio
async def test_whatsapp_link_uses_snapshots_not_altered_batch(
    client: AsyncClient,
    db_session: AsyncSession,
    active_cohort,
    pending_payment_session: PaymentSession,
):
    """Test that WhatsApp notification strictly references immutable snapshots even if parent Batch is modified."""
    _, batch = active_cohort

    # Mutate the parent batch after session creation
    batch.name = "Altered September Cohort"
    batch.amount_inr = 5000
    await db_session.flush()

    # Submit UTR
    utr_val = f"UTR_SNAP_{uuid.uuid4().hex[:8].upper()}"
    url = f"/v1/public/payment-sessions/{pending_payment_session.public_id}/submissions"
    res = await client.post(url, json={"utr": utr_val})
    assert res.status_code == 201

    wa_url = res.json()["whatsapp_url"]
    parsed_url = urllib.parse.urlparse(wa_url)
    decoded_message = urllib.parse.parse_qs(parsed_url.query)["text"][0]

    # Must contain original snapshot values, NOT mutated batch values
    assert "Batch: August 2026 Cohort" in decoded_message
    assert "Amount: ₹2,500" in decoded_message
    assert "Altered September Cohort" not in decoded_message
    assert "5,000" not in decoded_message


@pytest.mark.asyncio
async def test_public_payment_session_get_reflects_submitted_state(
    client: AsyncClient,
    pending_payment_session: PaymentSession,
):
    """Test that GET /v1/public/payment-sessions/{id} returns SUBMITTED state, masked UTR, and WhatsApp link after submission."""
    utr_val = f"UTR_GET_{uuid.uuid4().hex[:8].upper()}"
    submit_url = f"/v1/public/payment-sessions/{pending_payment_session.public_id}/submissions"

    sub_res = await client.post(submit_url, json={"utr": utr_val})
    assert sub_res.status_code == 201

    # Call GET payment session (simulating page reload)
    get_url = f"/v1/public/payment-sessions/{pending_payment_session.public_id}"
    get_res = await client.get(get_url)
    assert get_res.status_code == 200

    data = get_res.json()
    assert data["status"] == "SUBMITTED"
    assert data["utr_masked"] == mask_utr(utr_val)
    assert data["submitted_at"] is not None
    assert data["whatsapp_url"] is not None
    assert settings.ADMIN_WHATSAPP_NUMBER in data["whatsapp_url"]


# =============================================================================
# 3. LIVE CONCURRENCY & ROW LOCKING TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_concurrent_duplicate_utr_submissions_row_locking():
    """Live concurrency test: two simultaneous requests submitting the identical UTR to different sessions.

    Guarantees that PostgreSQL unique index serializes execution: exactly one succeeds and
    the other receives DuplicateUTRError.
    """
    app.dependency_overrides.clear()
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    service = PaymentSubmissionService()

    session_id_1 = None
    session_id_2 = None
    ps1_uuid = None
    ps2_uuid = None
    shared_utr = f"UTR_RACE_{uuid.uuid4().hex[:8].upper()}"

    # Setup 2 sessions
    async with session_factory() as setup_session:
        course = Course(public_id=uuid.uuid4(), name="Race Course")
        setup_session.add(course)
        await setup_session.flush()

        batch = Batch(public_id=uuid.uuid4(), course_id=course.id, name="Race Batch", amount_inr=1000)
        setup_session.add(batch)
        await setup_session.flush()

        ps1 = PaymentSession(
            public_id=uuid.uuid4(),
            full_name="Racer 1",
            phone="9876543210",
            email="r1@example.com",
            course_id=course.id,
            batch_id=batch.id,
            course_name_snapshot="Race Course",
            batch_name_snapshot="Race Batch",
            amount_inr=1000,
            reference_id=f"R1_{uuid.uuid4().hex[:6].upper()}",
            upi_id_snapshot="samagra@upi",
            payee_name_snapshot="Samagra",
            upi_uri="upi://pay",
            status="PENDING",
        )
        ps2 = PaymentSession(
            public_id=uuid.uuid4(),
            full_name="Racer 2",
            phone="9876543212",
            email="r2@example.com",
            course_id=course.id,
            batch_id=batch.id,
            course_name_snapshot="Race Course",
            batch_name_snapshot="Race Batch",
            amount_inr=1000,
            reference_id=f"R2_{uuid.uuid4().hex[:6].upper()}",
            upi_id_snapshot="samagra@upi",
            payee_name_snapshot="Samagra",
            upi_uri="upi://pay",
            status="PENDING",
        )
        setup_session.add_all([ps1, ps2])
        await setup_session.commit()
        session_id_1 = ps1.id
        session_id_2 = ps2.id
        ps1_uuid = ps1.public_id
        ps2_uuid = ps2.public_id

    # Concurrent worker task using separate db sessions
    async def worker_submit(session_uuid: uuid.UUID):
        async with session_factory() as db:
            try:
                await service.submit_utr_by_public_id(db, session_uuid, shared_utr)
                await db.commit()
                return "SUCCESS"
            except DuplicateUTRError:
                await db.rollback()
                return "DUPLICATE"
            except Exception as e:
                await db.rollback()
                return f"ERROR: {type(e).__name__}"

    results = await asyncio.gather(
        worker_submit(ps1_uuid),
        worker_submit(ps2_uuid),
        return_exceptions=False,
    )

    # Exactly one must succeed and one must be rejected as duplicate
    assert "SUCCESS" in results, f"One submission must succeed: {results}"
    assert "DUPLICATE" in results, f"Competing duplicate UTR must raise DuplicateUTRError: {results}"

    # Verify DB state
    async with session_factory() as verify_session:
        stmt = select(PaymentSubmission).where(PaymentSubmission.utr == shared_utr)
        subs = (await verify_session.execute(stmt)).scalars().all()
        assert len(subs) == 1, "Exactly one PaymentSubmission record must exist in DB."

        # Cleanup
        for s in subs:
            await verify_session.delete(s)
        await verify_session.flush()

        ps1_rec = await verify_session.get(PaymentSession, session_id_1)
        ps2_rec = await verify_session.get(PaymentSession, session_id_2)
        if ps1_rec:
            await verify_session.delete(ps1_rec)
        if ps2_rec:
            await verify_session.delete(ps2_rec)
        await verify_session.commit()

    await engine.dispose()


@pytest.mark.asyncio
async def test_concurrent_same_session_submissions_row_locking():
    """Live concurrency test: simultaneous UTR submissions for the same payment session."""
    app.dependency_overrides.clear()
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    service = PaymentSubmissionService()

    session_id = None
    ps_uuid = None

    async with session_factory() as setup_session:
        course = Course(public_id=uuid.uuid4(), name="Same Session Course")
        setup_session.add(course)
        await setup_session.flush()

        batch = Batch(public_id=uuid.uuid4(), course_id=course.id, name="Same Session Batch", amount_inr=1000)
        setup_session.add(batch)
        await setup_session.flush()

        ps = PaymentSession(
            public_id=uuid.uuid4(),
            full_name="Same User",
            phone="9876543210",
            email="same@example.com",
            course_id=course.id,
            batch_id=batch.id,
            course_name_snapshot="Same Session Course",
            batch_name_snapshot="Same Session Batch",
            amount_inr=1000,
            reference_id=f"SAME_{uuid.uuid4().hex[:6].upper()}",
            upi_id_snapshot="samagra@upi",
            payee_name_snapshot="Samagra",
            upi_uri="upi://pay",
            status="PENDING",
        )
        setup_session.add(ps)
        await setup_session.commit()
        session_id = ps.id
        ps_uuid = ps.public_id

    async def worker_submit(utr_val: str):
        async with session_factory() as db:
            try:
                await service.submit_utr_by_public_id(db, ps_uuid, utr_val)
                await db.commit()
                return "SUCCESS"
            except Exception as e:
                await db.rollback()
                return f"ERROR: {type(e).__name__}"

    utr_a = f"UTR_SAME_A_{uuid.uuid4().hex[:8].upper()}"
    utr_b = f"UTR_SAME_B_{uuid.uuid4().hex[:8].upper()}"

    results = await asyncio.gather(
        worker_submit(utr_a),
        worker_submit(utr_b),
        return_exceptions=False,
    )

    async with session_factory() as verify_session:
        # Check current submissions count
        stmt = select(PaymentSubmission).where(
            PaymentSubmission.payment_session_id == session_id,
            PaymentSubmission.is_current.is_(True),
        )
        current_subs = (await verify_session.execute(stmt)).scalars().all()
        assert len(current_subs) == 1, "Exactly one submission must remain current."

        # Check session status
        ps_stmt = select(PaymentSession).where(PaymentSession.id == session_id)
        final_ps = (await verify_session.execute(ps_stmt)).scalar_one()
        assert final_ps.status == "SUBMITTED"

        # Cleanup
        all_subs_stmt = select(PaymentSubmission).where(
            PaymentSubmission.payment_session_id == session_id
        )
        subs_to_delete = (await verify_session.execute(all_subs_stmt)).scalars().all()
        for s in subs_to_delete:
            await verify_session.delete(s)
        await verify_session.flush()

        course_id = final_ps.course_id
        batch_id = final_ps.batch_id
        await verify_session.delete(final_ps)
        await verify_session.flush()

        batch_to_delete = await verify_session.get(Batch, batch_id)
        if batch_to_delete:
            await verify_session.delete(batch_to_delete)
        course_to_delete = await verify_session.get(Course, course_id)
        if course_to_delete:
            await verify_session.delete(course_to_delete)
        await verify_session.commit()

    await engine.dispose()
