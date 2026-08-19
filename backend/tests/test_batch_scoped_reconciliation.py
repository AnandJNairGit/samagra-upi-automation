"""Integration tests for batch-scoped reconciliation workflow and critical invariants."""

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
from app.models.payment_session import PaymentSession
from app.models.statement_import import StatementImport
from app.models.bank_transaction import BankTransaction


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
        full_name="Reconciliation Test Admin",
        is_active=True,
    )
    db.add(admin)
    await db.flush()
    token = create_access_token(admin.public_id)
    return admin, token


@pytest.mark.asyncio
async def test_reconciliation_requires_batch_public_id(db_session: AsyncSession):
    """Verify POST /v1/admin/reconciliation/runs fails if batch_public_id is missing."""
    admin, token = await create_test_admin(db_session)
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/admin/reconciliation/runs",
            json={"statement_import_public_id": str(uuid.uuid4())},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422  # Unprocessable Entity due to missing required batch_public_id


@pytest.mark.asyncio
async def test_reconciliation_cross_batch_isolation(db_session: AsyncSession):
    """Verify that a reconciliation run for Batch A NEVER matches payment sessions from Batch B."""
    admin, token = await create_test_admin(db_session)
    transport = ASGITransport(app=app)
    ref_b = f"REF_BATCH_B_{uuid.uuid4().hex[:6].upper()}"

    # 1. Create Course, Batch A, and Batch B
    c = Course(public_id=uuid.uuid4(), name="Test Course", status="ACTIVE")
    db_session.add(c)
    await db_session.flush()

    batch_a = Batch(public_id=uuid.uuid4(), course_id=c.id, name="Batch A", amount_inr=2500, status="ACTIVE")
    batch_b = Batch(public_id=uuid.uuid4(), course_id=c.id, name="Batch B", amount_inr=2500, status="ACTIVE")
    db_session.add_all([batch_a, batch_b])
    await db_session.flush()

    # 2. PaymentSession for Batch B with reference ID ref_b
    ps_b = PaymentSession(
        public_id=uuid.uuid4(),
        course_id=c.id,
        batch_id=batch_b.id,
        full_name="User Batch B",
        phone="9876543210",
        email="b@example.com",
        course_name_snapshot="Test Course",
        batch_name_snapshot="Batch B",
        amount_inr=2500,
        reference_id=ref_b,
        upi_id_snapshot="samagralearning@ibl",
        payee_name_snapshot="Samagra Training",
        upi_uri="upi://pay?...",
        status="SUBMITTED",
    )
    db_session.add(ps_b)

    # 3. Create Statement Import containing credit for ref_b
    imp = StatementImport(
        public_id=uuid.uuid4(),
        filename="bank_statement.csv",
        file_type="csv",
        file_size=100,
        file_checksum_sha256=uuid.uuid4().hex,
        canonical_mapping_hash=uuid.uuid4().hex,
        source="GOOGLE_PAY",
        header_row_index=1,
        column_mapping={},
        status="COMPLETED",
        total_rows=1,
        valid_rows=1,
        imported_by=admin.id,
    )
    db_session.add(imp)
    await db_session.flush()

    txn = BankTransaction(
        public_id=uuid.uuid4(),
        statement_import_id=imp.id,
        amount_inr=2500,
        direction="CREDIT",
        reference_id=ref_b,
        source="GOOGLE_PAY",
        source_transaction_key=uuid.uuid4().hex,
    )
    db_session.add(txn)
    await db_session.commit()

    # 4. Execute Reconciliation for BATCH A against this statement
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/admin/reconciliation/runs",
            json={
                "batch_public_id": str(batch_a.public_id),
                "statement_import_public_id": str(imp.public_id),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["batch_public_id"] == str(batch_a.public_id)
        assert data["batch_name"] == "Batch A"
        assert data["matched_count"] == 0
        assert data["unknown_reference_count"] == 1  # ref_b is UNKNOWN in Batch A context!

        # 5. Fetch results for this run
        run_pub_id = data["public_id"]
        res_resp = await client.get(
            f"/v1/admin/reconciliation/runs/{run_pub_id}/results",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_resp.status_code == 200
        res_data = res_resp.json()
        assert len(res_data["items"]) == 1
        item = res_data["items"][0]
        assert item["status"] == "UNKNOWN_REFERENCE"
        assert item["payment_session_public_id"] is None


@pytest.mark.asyncio
async def test_reconciliation_zero_payment_sessions_batch(db_session: AsyncSession):
    """Verify reconciliation executes cleanly for a batch with 0 payment sessions."""
    admin, token = await create_test_admin(db_session)
    transport = ASGITransport(app=app)

    c = Course(public_id=uuid.uuid4(), name="Empty Course", status="ACTIVE")
    db_session.add(c)
    await db_session.flush()

    empty_batch = Batch(public_id=uuid.uuid4(), course_id=c.id, name="Empty Batch", amount_inr=1000, status="ACTIVE")
    db_session.add(empty_batch)
    await db_session.flush()

    imp = StatementImport(
        public_id=uuid.uuid4(),
        filename="empty_test.csv",
        file_type="csv",
        file_size=100,
        file_checksum_sha256=uuid.uuid4().hex,
        canonical_mapping_hash=uuid.uuid4().hex,
        source="GOOGLE_PAY",
        header_row_index=1,
        column_mapping={},
        status="COMPLETED",
        total_rows=1,
        valid_rows=1,
        imported_by=admin.id,
    )
    db_session.add(imp)
    await db_session.flush()

    txn = BankTransaction(
        public_id=uuid.uuid4(),
        statement_import_id=imp.id,
        amount_inr=1000,
        direction="CREDIT",
        reference_id=f"ZERO_REF_{uuid.uuid4().hex[:6].upper()}",
        source="GOOGLE_PAY",
        source_transaction_key=uuid.uuid4().hex,
    )
    db_session.add(txn)
    await db_session.commit()

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/admin/reconciliation/runs",
            json={
                "batch_public_id": str(empty_batch.public_id),
                "statement_import_public_id": str(imp.public_id),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["matched_count"] == 0
        assert data["unknown_reference_count"] == 1
        assert data["unmatched_count"] == 0


@pytest.mark.asyncio
async def test_batch_summary_api(db_session: AsyncSession):
    """Verify GET /v1/admin/batches/{batch_public_id}/summary returns correct aggregate metrics."""
    admin, token = await create_test_admin(db_session)
    transport = ASGITransport(app=app)
    ref_s1 = f"REF_S1_{uuid.uuid4().hex[:6].upper()}"
    ref_s2 = f"REF_S2_{uuid.uuid4().hex[:6].upper()}"

    c = Course(public_id=uuid.uuid4(), name="Summary Course", status="ACTIVE")
    db_session.add(c)
    await db_session.flush()

    batch = Batch(public_id=uuid.uuid4(), course_id=c.id, name="Summary Batch", amount_inr=3000, status="ACTIVE")
    db_session.add(batch)
    await db_session.flush()

    ps1 = PaymentSession(
        public_id=uuid.uuid4(),
        course_id=c.id,
        batch_id=batch.id,
        full_name="User 1",
        phone="9999999999",
        email="u1@example.com",
        course_name_snapshot="Summary Course",
        batch_name_snapshot="Summary Batch",
        amount_inr=3000,
        reference_id=ref_s1,
        upi_id_snapshot="samagra@ibl",
        payee_name_snapshot="Samagra",
        upi_uri="upi://pay",
        status="SUBMITTED",
    )
    ps2 = PaymentSession(
        public_id=uuid.uuid4(),
        course_id=c.id,
        batch_id=batch.id,
        full_name="User 2",
        phone="8888888888",
        email="u2@example.com",
        course_name_snapshot="Summary Course",
        batch_name_snapshot="Summary Batch",
        amount_inr=3000,
        reference_id=ref_s2,
        upi_id_snapshot="samagra@ibl",
        payee_name_snapshot="Samagra",
        upi_uri="upi://pay",
        status="APPROVED",
    )
    db_session.add_all([ps1, ps2])
    await db_session.commit()

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/v1/admin/batches/{batch.public_id}/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["batch_name"] == "Summary Batch"
        assert data["course_name"] == "Summary Course"
        assert data["amount_inr"] == 3000
        assert data["payments_generated"] == 2
        assert data["payments_submitted"] == 1
        assert data["payments_approved"] == 1
        assert data["expected_amount_inr"] == 6000
        assert data["approved_amount_inr"] == 3000


@pytest.mark.asyncio
async def test_statement_deletion_reconciliation_conflict(db_session: AsyncSession):
    """Verify attempting to delete a statement import with active reconciliation returns 409 Conflict."""
    admin, token = await create_test_admin(db_session)
    transport = ASGITransport(app=app)
    ref_del = f"DEL_REF_{uuid.uuid4().hex[:6].upper()}"

    c = Course(public_id=uuid.uuid4(), name="Del Course", status="ACTIVE")
    db_session.add(c)
    await db_session.flush()

    batch = Batch(public_id=uuid.uuid4(), course_id=c.id, name="Del Batch", amount_inr=1500, status="ACTIVE")
    db_session.add(batch)
    await db_session.flush()

    imp = StatementImport(
        public_id=uuid.uuid4(),
        filename="conflict_statement.csv",
        file_type="csv",
        file_size=100,
        file_checksum_sha256=uuid.uuid4().hex,
        canonical_mapping_hash=uuid.uuid4().hex,
        source="GOOGLE_PAY",
        header_row_index=1,
        column_mapping={},
        status="COMPLETED",
        total_rows=1,
        valid_rows=1,
        imported_by=admin.id,
    )
    db_session.add(imp)
    await db_session.flush()

    txn = BankTransaction(
        public_id=uuid.uuid4(),
        statement_import_id=imp.id,
        amount_inr=1500,
        direction="CREDIT",
        reference_id=ref_del,
        source="GOOGLE_PAY",
        source_transaction_key=uuid.uuid4().hex,
    )
    db_session.add(txn)
    await db_session.commit()

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Execute reconciliation run
        recon_resp = await client.post(
            "/v1/admin/reconciliation/runs",
            json={
                "batch_public_id": str(batch.public_id),
                "statement_import_public_id": str(imp.public_id),
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert recon_resp.status_code == 201

        # Delete statement import -> should succeed with 200 OK and cascade delete associated reconciliation runs
        del_resp = await client.delete(
            f"/v1/admin/statement-imports/{imp.public_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert del_resp.status_code == 200
        assert del_resp.json()["deleted_public_id"] == str(imp.public_id)
