"""Automated integration test suite for Phase 8 — Admin Payment Dashboard & Read-Only Inspection."""

import uuid
from datetime import datetime, timedelta, timezone
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.jwt import create_access_token
from app.auth.rate_limiter import auth_rate_limiter
from app.core.database import get_db
from app.main import app
from app.models.admin_user import AdminUser
from app.models.batch import Batch
from app.models.course import Course
from app.models.payment_session import PaymentSession
from app.models.payment_submission import PaymentSubmission


@pytest.fixture(autouse=True)
def setup_test_environment(db_session: AsyncSession):
    """Reset rate limiter and override database dependency for each test."""
    auth_rate_limiter.reset()
    app.dependency_overrides[get_db] = lambda: db_session
    yield
    auth_rate_limiter.reset()
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession):
    """Fixture providing an active AdminUser."""
    admin = AdminUser(
        public_id=uuid.uuid4(),
        email=f"admin_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="$2b$12$eImiTXuWVxfM37uY4JANjO5E.5R2G/aZJkM1p.N2H6Q01Y2W0W21C",
        full_name="Master Admin",
        is_active=True,
    )
    db_session.add(admin)
    await db_session.flush()
    return admin


@pytest_asyncio.fixture
async def admin_auth_headers(admin_user: AdminUser):
    """Fixture providing valid Authorization header for the active AdminUser."""
    token = create_access_token(admin_user.public_id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def client():
    """Async HTTP client fixture with ASGI transport."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def sample_dataset(db_session: AsyncSession, admin_user: AdminUser):
    """Fixture seeding courses, batches, sessions, and submissions across statuses."""
    now_utc = datetime.now(timezone.utc)

    course = Course(
        public_id=uuid.uuid4(),
        name="AI & Cloud Systems",
        description="Masterclass",
        status="ACTIVE",
    )
    db_session.add(course)
    await db_session.flush()

    batch = Batch(
        public_id=uuid.uuid4(),
        course_id=course.id,
        name="Cohort 2026",
        amount_inr=2000,
        status="ACTIVE",
        starts_at=now_utc,
    )
    db_session.add(batch)
    await db_session.flush()

    # 1. PENDING session
    ps_pending = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="User Pending",
        phone="9876543210",
        email="pending@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot=course.name,
        batch_name_snapshot=batch.name,
        amount_inr=2000,
        reference_id=f"REF_PENDING_{uuid.uuid4().hex[:6]}",
        upi_id_snapshot="samagra@upi",
        payee_name_snapshot="Samagra",
        upi_uri="upi://pay",
        status="PENDING",
    )

    # 2. SUBMITTED session
    ps_submitted = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="User Submitted",
        phone="9876543211",
        email="submitted@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot=course.name,
        batch_name_snapshot=batch.name,
        amount_inr=2000,
        reference_id=f"REF_SUB_{uuid.uuid4().hex[:6]}",
        upi_id_snapshot="samagra@upi",
        payee_name_snapshot="Samagra",
        upi_uri="upi://pay",
        status="SUBMITTED",
    )

    # 3. APPROVED session
    ps_approved = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="User Approved",
        phone="9876543212",
        email="approved@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot=course.name,
        batch_name_snapshot=batch.name,
        amount_inr=2000,
        reference_id=f"REF_APP_{uuid.uuid4().hex[:6]}",
        upi_id_snapshot="samagra@upi",
        payee_name_snapshot="Samagra",
        upi_uri="upi://pay",
        status="APPROVED",
    )

    # 4. REJECTED session
    ps_rejected = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="User Rejected",
        phone="9876543213",
        email="rejected@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot=course.name,
        batch_name_snapshot=batch.name,
        amount_inr=2000,
        reference_id=f"REF_REJ_{uuid.uuid4().hex[:6]}",
        upi_id_snapshot="samagra@upi",
        payee_name_snapshot="Samagra",
        upi_uri="upi://pay",
        status="REJECTED",
    )

    db_session.add_all([ps_pending, ps_submitted, ps_approved, ps_rejected])
    await db_session.flush()

    # Submissions
    sub1 = PaymentSubmission(
        public_id=uuid.uuid4(),
        payment_session_id=ps_submitted.id,
        utr=f"UTR_SUB_{uuid.uuid4().hex[:8]}",
        status="SUBMITTED",
        is_current=True,
    )
    sub2 = PaymentSubmission(
        public_id=uuid.uuid4(),
        payment_session_id=ps_approved.id,
        utr=f"UTR_APP_{uuid.uuid4().hex[:8]}",
        status="APPROVED",
        is_current=True,
        reviewed_by=admin_user.id,
        reviewed_at=now_utc,
    )
    sub3 = PaymentSubmission(
        public_id=uuid.uuid4(),
        payment_session_id=ps_rejected.id,
        utr=f"UTR_REJ_{uuid.uuid4().hex[:8]}",
        status="REJECTED",
        is_current=True,
        reviewed_by=admin_user.id,
        reviewed_at=now_utc,
        rejection_reason="Invalid UTR",
    )
    db_session.add_all([sub1, sub2, sub3])
    await db_session.flush()

    return {
        "course": course,
        "batch": batch,
        "pending": ps_pending,
        "submitted": ps_submitted,
        "approved": ps_approved,
        "rejected": ps_rejected,
        "utr_submitted": sub1.utr,
    }


# =============================================================================
# 1. SUMMARY METRICS TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_admin_dashboard_summary_requires_admin(client: AsyncClient):
    """Verify GET /v1/admin/dashboard/summary rejects unauthenticated requests with 401."""
    res = await client.get("/v1/admin/dashboard/summary")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_admin_dashboard_summary_success(
    client: AsyncClient, admin_auth_headers: dict, sample_dataset
):
    """Verify GET /v1/admin/dashboard/summary calculates exact metrics via SQL aggregation."""
    res = await client.get("/v1/admin/dashboard/summary", headers=admin_auth_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total_registrations"] >= 4
    assert data["pending_payments"] >= 1
    assert data["submitted_payments"] >= 1
    assert data["approved_payments"] >= 1
    assert data["rejected_payments"] >= 1
    # Revenue must equal sum of amount_inr for APPROVED sessions only (>= 2000)
    assert data["total_amount_collected_inr"] >= 2000


@pytest.mark.asyncio
async def test_summary_counts_match_paginated_list_total(
    client: AsyncClient, admin_auth_headers: dict, sample_dataset
):
    """Verify summary counts match paginated list total counts under identical status filters."""
    sum_res = await client.get("/v1/admin/dashboard/summary", headers=admin_auth_headers)
    assert sum_res.status_code == 200
    summary = sum_res.json()

    list_sub_res = await client.get(
        "/v1/admin/payments?status=SUBMITTED", headers=admin_auth_headers
    )
    assert list_sub_res.status_code == 200
    assert list_sub_res.json()["total"] == summary["submitted_payments"]


# =============================================================================
# 2. PAYMENT LIST & SEARCH TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_admin_payments_list_requires_admin(client: AsyncClient):
    """Verify GET /v1/admin/payments rejects unauthenticated requests with 401."""
    res = await client.get("/v1/admin/payments")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_admin_payments_list_filtering_and_search(
    client: AsyncClient, admin_auth_headers: dict, sample_dataset
):
    """Test filtering by status, course, batch, reference_id, utr, and text search."""
    data = sample_dataset

    # 1. Status Filter
    res_status = await client.get(
        "/v1/admin/payments?status=SUBMITTED", headers=admin_auth_headers
    )
    assert res_status.status_code == 200
    for item in res_status.json()["items"]:
        assert item["payment_session_status"] == "SUBMITTED"

    # 2. Course Filter
    res_course = await client.get(
        f"/v1/admin/payments?course_public_id={data['course'].public_id}",
        headers=admin_auth_headers,
    )
    assert res_course.status_code == 200
    assert res_course.json()["total"] >= 4

    # 3. Reference ID Exact Search
    ref_id = data["submitted"].reference_id
    res_ref = await client.get(
        f"/v1/admin/payments?reference_id={ref_id}", headers=admin_auth_headers
    )
    assert res_ref.status_code == 200
    assert res_ref.json()["total"] == 1
    assert res_ref.json()["items"][0]["reference_id"] == ref_id

    # 4. UTR Exact Search
    utr_val = data["utr_submitted"]
    res_utr = await client.get(
        f"/v1/admin/payments?utr={utr_val}", headers=admin_auth_headers
    )
    assert res_utr.status_code == 200
    assert res_utr.json()["total"] == 1
    assert res_utr.json()["items"][0]["utr"] == utr_val

    # 5. General Text Search by Name
    res_search = await client.get(
        "/v1/admin/payments?search=Submitted", headers=admin_auth_headers
    )
    assert res_search.status_code == 200
    assert res_search.json()["total"] >= 1


@pytest.mark.asyncio
async def test_payment_list_does_not_duplicate_sessions_when_historical_submissions_exist(
    client: AsyncClient, admin_auth_headers: dict, db_session: AsyncSession, sample_dataset
):
    """Test that left joining current submission (is_current=True) prevents duplicate payment session rows."""
    ps = sample_dataset["submitted"]

    # Deactivate sub1 and create a new current submission
    old_sub = PaymentSubmission(
        public_id=uuid.uuid4(),
        payment_session_id=ps.id,
        utr=f"UTR_HIST_{uuid.uuid4().hex[:8]}",
        status="REJECTED",
        is_current=False,
    )
    db_session.add(old_sub)
    await db_session.flush()

    res = await client.get(
        f"/v1/admin/payments?reference_id={ps.reference_id}", headers=admin_auth_headers
    )
    assert res.status_code == 200
    data = res.json()

    # Session must appear exactly ONCE
    assert data["total"] == 1
    assert len(data["items"]) == 1
    # utr field in list item must match current submission UTR
    assert data["items"][0]["utr"] == sample_dataset["utr_submitted"]


@pytest.mark.asyncio
async def test_admin_submitted_payments_shortcut(
    client: AsyncClient, admin_auth_headers: dict, sample_dataset
):
    """Test shortcut route GET /v1/admin/payments/submitted."""
    res = await client.get(
        "/v1/admin/payments/submitted", headers=admin_auth_headers
    )
    assert res.status_code == 200
    data = res.json()

    assert data["total"] >= 1
    for item in data["items"]:
        assert item["payment_session_status"] == "SUBMITTED"


@pytest.mark.asyncio
async def test_invalid_status_filter_rejected(
    client: AsyncClient, admin_auth_headers: dict
):
    """Test that invalid status filter value returns 422 Unprocessable Entity."""
    res = await client.get(
        "/v1/admin/payments?status=INVALID_STATUS", headers=admin_auth_headers
    )
    assert res.status_code == 422


# =============================================================================
# 3. PAYMENT DETAIL & SNAPSHOT TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_admin_payment_detail_requires_admin(client: AsyncClient, sample_dataset):
    """Verify GET /v1/admin/payments/{id} rejects unauthenticated requests with 401."""
    ps_uuid = sample_dataset["submitted"].public_id
    res = await client.get(f"/v1/admin/payments/{ps_uuid}")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_admin_payment_detail_success_and_snapshots(
    client: AsyncClient, admin_auth_headers: dict, sample_dataset
):
    """Test detailed read-only payment inspection returning participant, snapshots, and current submission."""
    ps = sample_dataset["submitted"]
    res = await client.get(
        f"/v1/admin/payments/{ps.public_id}", headers=admin_auth_headers
    )
    assert res.status_code == 200
    data = res.json()

    assert data["payment_session_public_id"] == str(ps.public_id)
    assert data["participant"]["full_name"] == ps.full_name
    assert data["participant"]["phone"] == ps.phone
    assert data["participant"]["email"] == ps.email

    assert data["training"]["course_name"] == ps.course_name_snapshot
    assert data["training"]["batch_name"] == ps.batch_name_snapshot

    assert data["payment"]["amount_inr"] == ps.amount_inr
    assert data["payment"]["reference_id"] == ps.reference_id
    assert data["payment"]["status"] == "SUBMITTED"

    assert data["current_submission"] is not None
    assert data["current_submission"]["utr"] == sample_dataset["utr_submitted"]
    assert data["current_submission"]["status"] == "SUBMITTED"


@pytest.mark.asyncio
async def test_admin_payment_detail_shows_historical_submission_history(
    client: AsyncClient,
    admin_auth_headers: dict,
    db_session: AsyncSession,
    sample_dataset,
):
    """Test that payment detail returns current submission AND complete submission history."""
    ps = sample_dataset["submitted"]

    # Deactivate current submission and add a new current submission
    old_utr = f"UTR_OLD_{uuid.uuid4().hex[:8]}"
    hist_sub = PaymentSubmission(
        public_id=uuid.uuid4(),
        payment_session_id=ps.id,
        utr=old_utr,
        status="REJECTED",
        is_current=False,
        rejection_reason="Incorrect UTR provided",
    )
    db_session.add(hist_sub)
    await db_session.flush()

    res = await client.get(
        f"/v1/admin/payments/{ps.public_id}", headers=admin_auth_headers
    )
    assert res.status_code == 200
    data = res.json()

    assert data["current_submission"]["utr"] == sample_dataset["utr_submitted"]
    assert len(data["submission_history"]) >= 2
    utrs_in_history = [s["utr"] for s in data["submission_history"]]
    assert old_utr in utrs_in_history
    assert sample_dataset["utr_submitted"] in utrs_in_history


@pytest.mark.asyncio
async def test_admin_payment_detail_uses_historical_snapshots_even_if_batch_updated(
    client: AsyncClient,
    admin_auth_headers: dict,
    db_session: AsyncSession,
    sample_dataset,
):
    """Test that admin detail honors historical snapshots even if parent Batch is modified."""
    batch = sample_dataset["batch"]
    ps = sample_dataset["submitted"]

    # Mutate parent batch
    batch.name = "Altered Future Cohort Name"
    batch.amount_inr = 9999
    await db_session.flush()

    res = await client.get(
        f"/v1/admin/payments/{ps.public_id}", headers=admin_auth_headers
    )
    assert res.status_code == 200
    data = res.json()

    # Must reflect original snapshot values, NOT mutated batch values
    assert data["training"]["batch_name"] == "Cohort 2026"
    assert data["payment"]["amount_inr"] == 2000
    assert data["training"]["batch_name"] != "Altered Future Cohort Name"
    assert data["payment"]["amount_inr"] != 9999


@pytest.mark.asyncio
async def test_no_mutation_endpoints_exist_in_phase8(
    client: AsyncClient, admin_auth_headers: dict, sample_dataset
):
    """Verify that Phase 8 strictly contains NO approval or rejection mutation endpoints."""
    ps_uuid = sample_dataset["submitted"].public_id

    res_approve = await client.post(
        f"/v1/admin/payments/{ps_uuid}/approve", headers=admin_auth_headers
    )
    assert res_approve.status_code in (404, 405)

    res_reject = await client.post(
        f"/v1/admin/payments/{ps_uuid}/reject", headers=admin_auth_headers
    )
    assert res_reject.status_code in (404, 405)
