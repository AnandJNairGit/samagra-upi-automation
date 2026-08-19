"""Pytest suite for Reconciliation Inspect Detail API (GET /v1/admin/reconciliation/results/{id})."""

import uuid
from datetime import datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.hashing import hash_password
from app.auth.jwt import create_access_token
from app.auth.rate_limiter import auth_rate_limiter
from app.core.database import get_db
from app.main import app
from app.models.admin_user import AdminUser
from app.models.bank_transaction import BankTransaction
from app.models.batch import Batch
from app.models.course import Course
from app.models.payment_session import PaymentSession
from app.models.payment_submission import PaymentSubmission
from app.models.reconciliation_result import ReconciliationResult
from app.models.reconciliation_run import ReconciliationRun
from app.models.statement_import import StatementImport
from app.services.reconciliation_service import ReconciliationService

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def setup_test_environment(db_session: AsyncSession):
    """Reset rate limiter and bind test database session to FastAPI dependency."""
    auth_rate_limiter.reset()
    app.dependency_overrides[get_db] = lambda: db_session
    yield
    auth_rate_limiter.reset()
    app.dependency_overrides.clear()


# Helper function to seed an admin user
async def create_test_admin(db: AsyncSession) -> AdminUser:
    admin = AdminUser(
        email=f"admin_{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("AdminPass123!"),
        full_name="Inspect Admin",
        is_active=True,
    )
    db.add(admin)
    await db.flush()
    return admin


# Helper function to seed course and batch
async def create_test_course_and_batch(db: AsyncSession, amount_inr: int = 5000) -> tuple[Course, Batch]:
    course = Course(
        name=f"Full Stack Web Development {uuid.uuid4().hex[:6]}",
        description="Comprehensive Bootcamp",
        status="ACTIVE",
    )
    db.add(course)
    await db.flush()

    batch = Batch(
        course_id=course.id,
        name=f"FSWD Morning Batch {uuid.uuid4().hex[:6]}",
        amount_inr=amount_inr,
        status="ACTIVE",
    )
    db.add(batch)
    await db.flush()
    return course, batch


# Helper function to seed payment session and optional submission
async def create_test_payment_session(
    db: AsyncSession,
    course: Course,
    batch: Batch,
    reference_id: str,
    status: str = "SUBMITTED",
    utr: str = None,
    full_name: str = "Aarav Sharma",
    phone: str = "9876543210",
    email: str = "aarav@example.com",
) -> tuple[PaymentSession, PaymentSubmission | None]:
    ps = PaymentSession(
        full_name=full_name,
        phone=phone,
        email=email,
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot=course.name,
        batch_name_snapshot=batch.name,
        amount_inr=batch.amount_inr,
        reference_id=reference_id,
        upi_id_snapshot="samagra@ibl",
        payee_name_snapshot="Samagra",
        upi_uri=f"upi://pay?pa=samagra@ibl&am={batch.amount_inr}&tr={reference_id}",
        status=status,
    )
    db.add(ps)
    await db.flush()

    sub = None
    if utr:
        sub = PaymentSubmission(
            payment_session_id=ps.id,
            utr=utr,
            status="SUBMITTED",
            is_current=True,
        )
        db.add(sub)
        await db.flush()

    return ps, sub


# Helper function to seed statement import and bank transactions with explicit raw_row_data
async def create_test_statement_import(
    db: AsyncSession,
    admin: AdminUser,
    transactions: list[dict],
    filename: str = "bank_statement_jan2026.csv",
) -> tuple[StatementImport, list[BankTransaction]]:
    si = StatementImport(
        filename=filename,
        file_type="csv",
        file_size=1024,
        file_checksum_sha256=uuid.uuid4().hex,
        canonical_mapping_hash=uuid.uuid4().hex,
        column_mapping={"reference_id": {"column_index": 2}, "amount": {"column_index": 4}},
        status="COMPLETED",
        total_rows=len(transactions),
        valid_rows=len(transactions),
        imported_by=admin.id,
    )
    db.add(si)
    await db.flush()

    created_txs = []
    for idx, t in enumerate(transactions, start=1):
        raw_row = t.get("raw_row_data") or {
            "Date": "2026-01-15",
            "Description": t.get("description", "UPI payment received"),
            "Ref No": t.get("reference_id", ""),
            "Direction": t.get("direction", "CREDIT"),
            "Amount": str(t.get("amount_inr", 5000)),
            "UTR": t.get("utr", ""),
        }
        bt = BankTransaction(
            statement_import_id=si.id,
            transaction_at=t.get("transaction_at", datetime.now(timezone.utc)),
            amount_inr=t.get("amount_inr", 5000),
            direction=t.get("direction", "CREDIT"),
            reference_id=t.get("reference_id"),
            utr=t.get("utr"),
            counterparty_name=t.get("counterparty_name", "Aarav Sharma"),
            description=t.get("description", "UPI-12345"),
            source="GOOGLE_PAY",
            source_transaction_key=f"TXN_KEY_{uuid.uuid4().hex}",
            raw_row_data=raw_row,
        )
        db.add(bt)
        created_txs.append(bt)

    await db.flush()
    return si, created_txs


async def test_detail_matched_with_raw_row_data(db_session: AsyncSession):
    """Test GET /v1/admin/reconciliation/results/{id} returns complete matched details with raw_row_data."""
    admin = await create_test_admin(db_session)
    token = create_access_token(admin.public_id)
    course, batch = await create_test_course_and_batch(db_session, amount_inr=5000)
    ref_code = f"REF_MATCH_{uuid.uuid4().hex[:6].upper()}"
    utr_num = "987654321012"

    ps, sub = await create_test_payment_session(
        db_session, course, batch, ref_code, status="SUBMITTED", utr=utr_num, full_name="Aarav Sharma"
    )

    custom_raw = {
        "Date": "2026-01-15",
        "Description": "UPI payment from Aarav Sharma",
        "Ref No": ref_code,
        "Direction": "CREDIT",
        "Amount": "5,000.00",
        "UTR": utr_num,
    }

    si, txs = await create_test_statement_import(
        db_session,
        admin,
        [
            {
                "direction": "CREDIT",
                "reference_id": ref_code,
                "amount_inr": 5000,
                "utr": utr_num,
                "counterparty_name": "Aarav Sharma",
                "description": "UPI payment from Aarav Sharma",
                "raw_row_data": custom_raw,
            }
        ],
        filename="hdfc_jan_2026.xlsx",
    )

    service = ReconciliationService()
    run_res = await service.run_reconciliation(db_session, batch.public_id, si.public_id, admin)
    assert run_res.matched_count == 1

    results_res = await service.list_results_for_run_paginated(db_session, run_res.public_id)
    result_public_id = results_res.items[0].public_id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/v1/admin/reconciliation/results/{result_public_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Verdict
        assert data["status"] == "MATCHED"
        assert data["reason_code"] == "MATCHED_REFERENCE_AMOUNT"
        assert data["reference_match"] is True
        assert data["amount_match"] is True
        assert data["utr_match"] is True

        # Raw Row Data
        assert data["raw_row_data"] is not None
        assert data["raw_row_data"]["Ref No"] == ref_code
        assert data["raw_row_data"]["Amount"] == "5,000.00"
        assert data["raw_row_data"]["UTR"] == utr_num

        # Bank Fields
        assert data["statement_filename"] == "hdfc_jan_2026.xlsx"
        assert data["bank_reference_id"] == ref_code
        assert data["bank_amount_inr"] == 5000
        assert data["bank_utr"] == utr_num
        assert data["bank_counterparty_name"] == "Aarav Sharma"
        assert data["bank_direction"] == "CREDIT"

        # Application Payment Fields
        assert data["expected_reference_id"] == ref_code
        assert data["expected_amount_inr"] == 5000
        assert data["participant_name"] == "Aarav Sharma"
        assert data["course_name_snapshot"] == course.name
        assert data["batch_name_snapshot"] == batch.name
        assert data["submitted_utr"] == utr_num
        assert data["submission_status"] in ("APPROVED", "SUBMITTED")


async def test_detail_raw_row_data_is_original_not_normalized(db_session: AsyncSession):
    """Test that raw spreadsheet values (e.g. formatted string '5,000.00') are preserved verbatim without being replaced by normalized values."""
    admin = await create_test_admin(db_session)
    token = create_access_token(admin.public_id)
    course, batch = await create_test_course_and_batch(db_session, amount_inr=5000)
    ref_code = f"REF_RAW_{uuid.uuid4().hex[:6].upper()}"

    ps, sub = await create_test_payment_session(db_session, course, batch, ref_code, status="SUBMITTED")

    raw_cell_amount = "5,000.00"
    si, txs = await create_test_statement_import(
        db_session,
        admin,
        [
            {
                "direction": "CREDIT",
                "reference_id": ref_code,
                "amount_inr": 5000,
                "raw_row_data": {
                    "Txn Date": "15/01/2026",
                    "Narration": f"UPI/CR/{ref_code}/PAYMENT",
                    "Ref No": ref_code,
                    "Amount": raw_cell_amount,
                },
            }
        ],
    )

    service = ReconciliationService()
    run_res = await service.run_reconciliation(db_session, batch.public_id, si.public_id, admin)

    results_res = await service.list_results_for_run_paginated(db_session, run_res.public_id)
    result_public_id = results_res.items[0].public_id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/v1/admin/reconciliation/results/{result_public_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Invariant: Raw row preserves exact string '5,000.00' while normalized amount is int 5000
        assert data["raw_row_data"]["Amount"] == "5,000.00"
        assert data["bank_amount_inr"] == 5000
        assert data["expected_amount_inr"] == 5000


async def test_detail_raw_row_preserves_xlsx_native_values(db_session: AsyncSession):
    """Test that XLSX-derived numeric cells, ISO date strings, booleans, and nulls are safely serialized in raw_row_data."""
    admin = await create_test_admin(db_session)
    token = create_access_token(admin.public_id)
    course, batch = await create_test_course_and_batch(db_session, amount_inr=5000)
    ref_code = f"REF_XLSX_{uuid.uuid4().hex[:6].upper()}"

    await create_test_payment_session(db_session, course, batch, ref_code, status="SUBMITTED")

    xlsx_raw = {
        "Date": "2026-01-15T10:30:00+00:00",
        "NumericAmount": 5000,
        "FloatFee": 0.0,
        "IsCredit": True,
        "OptionalRemarks": None,
        "Ref No": ref_code,
    }

    si, txs = await create_test_statement_import(
        db_session,
        admin,
        [
            {
                "direction": "CREDIT",
                "reference_id": ref_code,
                "amount_inr": 5000,
                "raw_row_data": xlsx_raw,
            }
        ],
    )

    service = ReconciliationService()
    run_res = await service.run_reconciliation(db_session, batch.public_id, si.public_id, admin)

    results_res = await service.list_results_for_run_paginated(db_session, run_res.public_id)
    result_public_id = results_res.items[0].public_id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/v1/admin/reconciliation/results/{result_public_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["raw_row_data"]["NumericAmount"] == 5000
        assert data["raw_row_data"]["FloatFee"] == 0.0
        assert data["raw_row_data"]["IsCredit"] is True
        assert data["raw_row_data"]["OptionalRemarks"] is None


async def test_detail_does_not_leak_internal_ids(db_session: AsyncSession):
    """Test that the detail API response does not expose internal database IDs."""
    admin = await create_test_admin(db_session)
    token = create_access_token(admin.public_id)
    course, batch = await create_test_course_and_batch(db_session, amount_inr=5000)
    ref_code = f"REF_SEC_{uuid.uuid4().hex[:6].upper()}"

    ps, sub = await create_test_payment_session(db_session, course, batch, ref_code, status="SUBMITTED", utr="123")
    si, txs = await create_test_statement_import(
        db_session, admin, [{"direction": "CREDIT", "reference_id": ref_code, "amount_inr": 5000, "utr": "123"}]
    )

    service = ReconciliationService()
    run_res = await service.run_reconciliation(db_session, batch.public_id, si.public_id, admin)

    results_res = await service.list_results_for_run_paginated(db_session, run_res.public_id)
    result_public_id = results_res.items[0].public_id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/v1/admin/reconciliation/results/{result_public_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Forbidden internal fields
        assert "id" not in data
        assert "admin_user_id" not in data
        assert "statement_import_id" not in data
        assert "payment_session_id" not in data
        assert "bank_transaction_id" not in data

        # Permitted public UUIDs
        assert "public_id" in data
        assert "reconciliation_run_public_id" in data
        assert "bank_transaction_public_id" in data
        assert "payment_session_public_id" in data


async def test_detail_amount_mismatch(db_session: AsyncSession):
    """Test detail inspection for an AMOUNT_MISMATCH transaction."""
    admin = await create_test_admin(db_session)
    token = create_access_token(admin.public_id)
    course, batch = await create_test_course_and_batch(db_session, amount_inr=5000)
    ref_code = f"REF_AMT_MIS_{uuid.uuid4().hex[:6].upper()}"

    ps, sub = await create_test_payment_session(db_session, course, batch, ref_code, status="SUBMITTED")

    si, txs = await create_test_statement_import(
        db_session, admin, [{"direction": "CREDIT", "reference_id": ref_code, "amount_inr": 4500}]
    )

    service = ReconciliationService()
    run_res = await service.run_reconciliation(db_session, batch.public_id, si.public_id, admin)
    assert run_res.amount_mismatch_count == 1

    results_res = await service.list_results_for_run_paginated(db_session, run_res.public_id)
    result_public_id = results_res.items[0].public_id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/v1/admin/reconciliation/results/{result_public_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "AMOUNT_MISMATCH"
        assert data["reason_code"] == "AMOUNT_MISMATCH"
        assert data["reference_match"] is True
        assert data["amount_match"] is False
        assert data["bank_amount_inr"] == 4500
        assert data["expected_amount_inr"] == 5000


async def test_detail_utr_mismatch(db_session: AsyncSession):
    """Test detail inspection for a UTR_MISMATCH transaction."""
    admin = await create_test_admin(db_session)
    token = create_access_token(admin.public_id)
    course, batch = await create_test_course_and_batch(db_session, amount_inr=5000)
    ref_code = f"REF_UTR_MIS_{uuid.uuid4().hex[:6].upper()}"

    ps, sub = await create_test_payment_session(
        db_session, course, batch, ref_code, status="SUBMITTED", utr="111111111111"
    )

    si, txs = await create_test_statement_import(
        db_session, admin, [{"direction": "CREDIT", "reference_id": ref_code, "amount_inr": 5000, "utr": "999999999999"}]
    )

    service = ReconciliationService()
    run_res = await service.run_reconciliation(db_session, batch.public_id, si.public_id, admin)
    assert run_res.utr_mismatch_count == 1

    results_res = await service.list_results_for_run_paginated(db_session, run_res.public_id)
    result_public_id = results_res.items[0].public_id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/v1/admin/reconciliation/results/{result_public_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "UTR_MISMATCH"
        assert data["reason_code"] == "UTR_MISMATCH"
        assert data["reference_match"] is True
        assert data["amount_match"] is True
        assert data["utr_match"] is False
        assert data["bank_utr"] == "999999999999"
        assert data["submitted_utr"] == "111111111111"


async def test_detail_unknown_reference(db_session: AsyncSession):
    """Test detail inspection for an UNKNOWN_REFERENCE transaction."""
    admin = await create_test_admin(db_session)
    token = create_access_token(admin.public_id)
    course, batch = await create_test_course_and_batch(db_session, amount_inr=5000)

    si, txs = await create_test_statement_import(
        db_session, admin, [{"direction": "CREDIT", "reference_id": "UNKNOWN_REF_999", "amount_inr": 5000}]
    )

    service = ReconciliationService()
    run_res = await service.run_reconciliation(db_session, batch.public_id, si.public_id, admin)
    assert run_res.unknown_reference_count == 1

    results_res = await service.list_results_for_run_paginated(db_session, run_res.public_id)
    result_public_id = results_res.items[0].public_id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/v1/admin/reconciliation/results/{result_public_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "UNKNOWN_REFERENCE"
        assert data["payment_session_public_id"] is None
        assert data["expected_reference_id"] is None
        assert data["expected_amount_inr"] is None
        assert data["participant_name"] is None
        assert data["bank_reference_id"] == "UNKNOWN_REF_999"
        assert data["raw_row_data"] is not None


async def test_detail_no_reference(db_session: AsyncSession):
    """Test detail inspection for a NO_REFERENCE transaction."""
    admin = await create_test_admin(db_session)
    token = create_access_token(admin.public_id)
    course, batch = await create_test_course_and_batch(db_session, amount_inr=5000)

    si, txs = await create_test_statement_import(
        db_session, admin, [{"direction": "CREDIT", "reference_id": "", "amount_inr": 5000}]
    )

    service = ReconciliationService()
    run_res = await service.run_reconciliation(db_session, batch.public_id, si.public_id, admin)
    assert run_res.no_reference_count == 1

    results_res = await service.list_results_for_run_paginated(db_session, run_res.public_id)
    result_public_id = results_res.items[0].public_id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/v1/admin/reconciliation/results/{result_public_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "NO_REFERENCE"
        assert data["reference_match"] is None
        assert not data["bank_reference_id"]
        assert data["raw_row_data"] is not None


async def test_detail_optional_utr_handling(db_session: AsyncSession):
    """Test that missing submission UTR produces utr_match=None cleanly without errors."""
    admin = await create_test_admin(db_session)
    token = create_access_token(admin.public_id)
    course, batch = await create_test_course_and_batch(db_session, amount_inr=5000)
    ref_code = f"REF_NO_UTR_{uuid.uuid4().hex[:6].upper()}"

    ps, sub = await create_test_payment_session(db_session, course, batch, ref_code, status="SUBMITTED", utr=None)

    si, txs = await create_test_statement_import(
        db_session, admin, [{"direction": "CREDIT", "reference_id": ref_code, "amount_inr": 5000, "utr": "987654321098"}]
    )

    service = ReconciliationService()
    run_res = await service.run_reconciliation(db_session, batch.public_id, si.public_id, admin)
    assert run_res.matched_count == 1

    results_res = await service.list_results_for_run_paginated(db_session, run_res.public_id)
    result_public_id = results_res.items[0].public_id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/v1/admin/reconciliation/results/{result_public_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "MATCHED"
        assert data["submitted_utr"] is None
        assert data["utr_match"] is None  # Evaluated as None (Not provided by participant)


async def test_detail_unauthenticated_401():
    """Test unauthenticated request to detail endpoint returns 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(f"/v1/admin/reconciliation/results/{uuid.uuid4()}")
        assert response.status_code == 401


async def test_detail_nonexistent_404(db_session: AsyncSession):
    """Test requesting a nonexistent reconciliation result returns 404."""
    admin = await create_test_admin(db_session)
    token = create_access_token(admin.public_id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            f"/v1/admin/reconciliation/results/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404
