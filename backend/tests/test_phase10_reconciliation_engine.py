"""Automated Pytest integration suite for Phase 10 — Reconciliation Engine."""

import uuid
from datetime import datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.hashing import hash_password
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


# Helper function to seed an admin user
async def create_test_admin(db: AsyncSession) -> AdminUser:
    admin = AdminUser(
        email=f"admin_{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("AdminPass123!"),
        full_name="Reconciliation Admin",
        is_active=True,
    )
    db.add(admin)
    await db.flush()
    return admin


# Helper function to seed course and batch
async def create_test_course_and_batch(db: AsyncSession, amount_inr: int = 2500) -> tuple[Course, Batch]:
    course = Course(
        name=f"Python Bootcamp {uuid.uuid4().hex[:6]}",
        description="Bootcamp",
        status="ACTIVE",
    )
    db.add(course)
    await db.flush()

    batch = Batch(
        course_id=course.id,
        name=f"Batch 2026 {uuid.uuid4().hex[:6]}",
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
) -> tuple[PaymentSession, PaymentSubmission | None]:
    ps = PaymentSession(
        full_name="Alice Smith",
        phone="9876543210",
        email="alice@example.com",
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


# Helper function to seed statement import and bank transactions
async def create_test_statement_import(
    db: AsyncSession, admin: AdminUser, transactions_data: list[dict]
) -> tuple[StatementImport, list[BankTransaction]]:
    si = StatementImport(
        filename="test_statement.csv",
        file_type="csv",
        file_size=1024,
        file_checksum_sha256=uuid.uuid4().hex,
        canonical_mapping_hash=uuid.uuid4().hex,
        column_mapping={"reference_id": {"column_index": 0}, "amount": {"column_index": 1}},
        status="COMPLETED",
        total_rows=len(transactions_data),
        valid_rows=len(transactions_data),
        imported_by=admin.id,
    )
    db.add(si)
    await db.flush()

    tx_entities = []
    for data in transactions_data:
        bt = BankTransaction(
            statement_import_id=si.id,
            direction=data.get("direction", "CREDIT"),
            reference_id=data.get("reference_id"),
            amount_inr=data.get("amount_inr"),
            utr=data.get("utr"),
            counterparty_name=data.get("counterparty_name", "Payer Name"),
            source="GOOGLE_PAY",
        )
        db.add(bt)
        tx_entities.append(bt)

    await db.flush()
    return si, tx_entities


# -----------------------------------------------------------------------------
# Pytest Test Cases
# -----------------------------------------------------------------------------

async def test_credit_reference_amount_match(db_session: AsyncSession):
    """Test exact reference code and amount match yields MATCHED status."""
    admin = await create_test_admin(db_session)
    course, batch = await create_test_course_and_batch(db_session, amount_inr=2500)
    ref_code = f"ALICE_3210_{uuid.uuid4().hex[:4].upper()}"
    utr_num = f"1234{uuid.uuid4().hex[:8]}"

    ps, sub = await create_test_payment_session(db_session, course, batch, ref_code, status="SUBMITTED", utr=utr_num)

    si, txs = await create_test_statement_import(
        db_session,
        admin,
        [{"direction": "CREDIT", "reference_id": ref_code, "amount_inr": 2500, "utr": utr_num}],
    )

    service = ReconciliationService()
    run_res = await service.run_reconciliation(db_session, si.public_id, admin)

    assert run_res.status == "COMPLETED"
    assert run_res.total_transactions == 1
    assert run_res.matched_count == 1
    assert run_res.amount_mismatch_count == 0

    results_res = await service.list_results_for_run_paginated(db_session, run_res.public_id)
    assert len(results_res.items) == 1
    res = results_res.items[0]

    assert res.status == "MATCHED"
    assert res.reason_code == "MATCHED_REFERENCE_AMOUNT"
    assert res.reference_match is True
    assert res.amount_match is True
    assert res.utr_match is True
    assert res.payment_session_public_id == ps.public_id


async def test_pending_payment_session_can_be_reconciled(db_session: AsyncSession):
    """Test PENDING payment session (no submission) matches cleanly as MATCHED while leaving session status PENDING."""
    admin = await create_test_admin(db_session)
    course, batch = await create_test_course_and_batch(db_session, amount_inr=3000)
    ref_code = f"BOB_4321_{uuid.uuid4().hex[:4].upper()}"

    # PaymentSession in PENDING state with NO PaymentSubmission
    ps, sub = await create_test_payment_session(db_session, course, batch, ref_code, status="PENDING", utr=None)

    si, txs = await create_test_statement_import(
        db_session,
        admin,
        [{"direction": "CREDIT", "reference_id": ref_code, "amount_inr": 3000, "utr": "999988887777"}],
    )

    service = ReconciliationService()
    run_res = await service.run_reconciliation(db_session, si.public_id, admin)

    assert run_res.matched_count == 1

    results_res = await service.list_results_for_run_paginated(db_session, run_res.public_id)
    res = results_res.items[0]

    assert res.status == "MATCHED"
    assert res.reference_match is True
    assert res.amount_match is True
    assert res.utr_match is None  # Missing submitted UTR => None
    assert res.payment_session_public_id == ps.public_id
    assert res.payment_submission_public_id is None

    # CRITICAL: Verify payment session status remains PENDING
    await db_session.refresh(ps)
    assert ps.status == "PENDING"


async def test_reference_amount_match_without_payment_submission(db_session: AsyncSession):
    """Test reference and amount match when user never submitted a UTR."""
    admin = await create_test_admin(db_session)
    course, batch = await create_test_course_and_batch(db_session, amount_inr=1500)
    ref_code = f"CHARLIE_1111_{uuid.uuid4().hex[:4].upper()}"

    ps, sub = await create_test_payment_session(db_session, course, batch, ref_code, status="PENDING", utr=None)

    si, txs = await create_test_statement_import(
        db_session,
        admin,
        [{"direction": "CREDIT", "reference_id": ref_code, "amount_inr": 1500, "utr": None}],
    )

    service = ReconciliationService()
    run_res = await service.run_reconciliation(db_session, si.public_id, admin)

    assert run_res.matched_count == 1
    results_res = await service.list_results_for_run_paginated(db_session, run_res.public_id)
    res = results_res.items[0]

    assert res.status == "MATCHED"
    assert res.payment_session_public_id == ps.public_id
    assert res.payment_submission_public_id is None
    assert res.utr_match is None


async def test_reference_match_utr_mismatch(db_session: AsyncSession):
    """Test reference and amount match with differing UTR yields UTR_MISMATCH status."""
    admin = await create_test_admin(db_session)
    course, batch = await create_test_course_and_batch(db_session, amount_inr=2000)
    ref_code = f"DAVID_2222_{uuid.uuid4().hex[:4].upper()}"

    ps, sub = await create_test_payment_session(db_session, course, batch, ref_code, status="SUBMITTED", utr="SUBMITTED_UTR_123")

    si, txs = await create_test_statement_import(
        db_session,
        admin,
        [{"direction": "CREDIT", "reference_id": ref_code, "amount_inr": 2000, "utr": "DIFFERENT_BANK_UTR_999"}],
    )

    service = ReconciliationService()
    run_res = await service.run_reconciliation(db_session, si.public_id, admin)

    assert run_res.utr_mismatch_count == 1
    assert run_res.matched_count == 0

    results_res = await service.list_results_for_run_paginated(db_session, run_res.public_id)
    res = results_res.items[0]

    assert res.status == "UTR_MISMATCH"
    assert res.reason_code == "UTR_MISMATCH"
    assert res.reference_match is True
    assert res.amount_match is True
    assert res.utr_match is False


async def test_amount_mismatch(db_session: AsyncSession):
    """Test matching reference code with differing bank amount yields AMOUNT_MISMATCH status."""
    admin = await create_test_admin(db_session)
    course, batch = await create_test_course_and_batch(db_session, amount_inr=2500)
    ref_code = f"EVA_3333_{uuid.uuid4().hex[:4].upper()}"

    ps, sub = await create_test_payment_session(db_session, course, batch, ref_code, status="SUBMITTED", utr="123456789012")

    # Bank statement has ₹2000 instead of ₹2500
    si, txs = await create_test_statement_import(
        db_session,
        admin,
        [{"direction": "CREDIT", "reference_id": ref_code, "amount_inr": 2000, "utr": "123456789012"}],
    )

    service = ReconciliationService()
    run_res = await service.run_reconciliation(db_session, si.public_id, admin)

    assert run_res.amount_mismatch_count == 1
    assert run_res.matched_count == 0

    results_res = await service.list_results_for_run_paginated(db_session, run_res.public_id)
    res = results_res.items[0]

    assert res.status == "AMOUNT_MISMATCH"
    assert res.reason_code == "AMOUNT_MISMATCH"
    assert res.reference_match is True
    assert res.amount_match is False


async def test_unknown_reference(db_session: AsyncSession):
    """Test statement transaction with nonexistent reference code yields UNKNOWN_REFERENCE."""
    admin = await create_test_admin(db_session)
    unknown_ref = f"NONEXISTENT_REF_{uuid.uuid4().hex[:4].upper()}"

    si, txs = await create_test_statement_import(
        db_session,
        admin,
        [{"direction": "CREDIT", "reference_id": unknown_ref, "amount_inr": 2500}],
    )

    service = ReconciliationService()
    run_res = await service.run_reconciliation(db_session, si.public_id, admin)

    assert run_res.unknown_reference_count == 1

    results_res = await service.list_results_for_run_paginated(db_session, run_res.public_id)
    res = results_res.items[0]

    assert res.status == "UNKNOWN_REFERENCE"
    assert res.reason_code == "UNKNOWN_REFERENCE"
    assert res.reference_match is False
    assert res.amount_match is None


async def test_missing_reference(db_session: AsyncSession):
    """Test statement transaction with blank reference code yields NO_REFERENCE."""
    admin = await create_test_admin(db_session)

    si, txs = await create_test_statement_import(
        db_session,
        admin,
        [{"direction": "CREDIT", "reference_id": "", "amount_inr": 2500}],
    )

    service = ReconciliationService()
    run_res = await service.run_reconciliation(db_session, si.public_id, admin)

    assert run_res.no_reference_count == 1

    results_res = await service.list_results_for_run_paginated(db_session, run_res.public_id)
    res = results_res.items[0]

    assert res.status == "NO_REFERENCE"
    assert res.reason_code == "NO_REFERENCE"
    assert res.reference_match is None


async def test_non_credit_transaction(db_session: AsyncSession):
    """Test DEBIT statement transaction yields UNMATCHED."""
    admin = await create_test_admin(db_session)

    si, txs = await create_test_statement_import(
        db_session,
        admin,
        [{"direction": "DEBIT", "reference_id": "SOME_REF", "amount_inr": 500}],
    )

    service = ReconciliationService()
    run_res = await service.run_reconciliation(db_session, si.public_id, admin)

    assert run_res.unmatched_count == 1
    assert run_res.debit_transactions == 1

    results_res = await service.list_results_for_run_paginated(db_session, run_res.public_id)
    res = results_res.items[0]

    assert res.status == "UNMATCHED"
    assert res.reason_code == "NON_CREDIT_TRANSACTION"


async def test_duplicate_reference_transaction(db_session: AsyncSession):
    """Test multiple bank transactions in one import sharing the same reference code yields DUPLICATE_TRANSACTION."""
    admin = await create_test_admin(db_session)
    course, batch = await create_test_course_and_batch(db_session, amount_inr=2500)
    ref_code = f"DUP_REF_{uuid.uuid4().hex[:4].upper()}"

    ps, sub = await create_test_payment_session(db_session, course, batch, ref_code, status="SUBMITTED", utr="111")

    # Two transactions in same import with identical reference code
    si, txs = await create_test_statement_import(
        db_session,
        admin,
        [
            {"direction": "CREDIT", "reference_id": ref_code, "amount_inr": 2500},
            {"direction": "CREDIT", "reference_id": ref_code, "amount_inr": 2500},
        ],
    )

    service = ReconciliationService()
    run_res = await service.run_reconciliation(db_session, si.public_id, admin)

    assert run_res.duplicate_transaction_count == 2
    assert run_res.matched_count == 0

    results_res = await service.list_results_for_run_paginated(db_session, run_res.public_id)
    for res in results_res.items:
        assert res.status == "DUPLICATE_TRANSACTION"
        assert res.reason_code == "DUPLICATE_TRANSACTION"


async def test_phase_boundary_payment_status_unmutated(db_session: AsyncSession):
    """MANDATORY PHASE BOUNDARY TEST: Verifies payment session and submission statuses remain completely unmutated."""
    admin = await create_test_admin(db_session)
    course, batch = await create_test_course_and_batch(db_session, amount_inr=2500)
    ref_code = f"BOUNDARY_TEST_{uuid.uuid4().hex[:4].upper()}"
    utr_num = "987654321098"

    ps, sub = await create_test_payment_session(db_session, course, batch, ref_code, status="SUBMITTED", utr=utr_num)

    si, txs = await create_test_statement_import(
        db_session,
        admin,
        [{"direction": "CREDIT", "reference_id": ref_code, "amount_inr": 2500, "utr": utr_num}],
    )

    # Initial assertion
    assert ps.status == "SUBMITTED"
    assert sub.status == "SUBMITTED"

    service = ReconciliationService()
    run_res = await service.run_reconciliation(db_session, si.public_id, admin)

    assert run_res.matched_count == 1

    # Refresh entities from DB session
    await db_session.refresh(ps)
    await db_session.refresh(sub)

    # ABSOLUTE ASSERTION: Status MUST remain SUBMITTED (NOT APPROVED / VERIFIED)
    assert ps.status == "SUBMITTED"
    assert sub.status == "SUBMITTED"
    assert ps.amount_inr == 2500
    assert ps.reference_id == ref_code
    assert sub.utr == utr_num


async def test_rerun_determinism(db_session: AsyncSession):
    """Test running reconciliation twice on the same statement file produces identical result classifications in two separate runs."""
    admin = await create_test_admin(db_session)
    course, batch = await create_test_course_and_batch(db_session, amount_inr=2500)
    ref_code = f"RERUN_REF_{uuid.uuid4().hex[:4].upper()}"

    ps, sub = await create_test_payment_session(db_session, course, batch, ref_code, status="SUBMITTED", utr="123")

    si, txs = await create_test_statement_import(
        db_session,
        admin,
        [{"direction": "CREDIT", "reference_id": ref_code, "amount_inr": 2500, "utr": "123"}],
    )

    service = ReconciliationService()

    # Run 1
    run1 = await service.run_reconciliation(db_session, si.public_id, admin)
    res1 = await service.list_results_for_run_paginated(db_session, run1.public_id)

    # Run 2
    run2 = await service.run_reconciliation(db_session, si.public_id, admin)
    res2 = await service.list_results_for_run_paginated(db_session, run2.public_id)

    assert run1.public_id != run2.public_id
    assert run1.matched_count == run2.matched_count == 1
    assert res1.items[0].status == res2.items[0].status == "MATCHED"


async def test_summary_metrics_consistency(db_session: AsyncSession):
    """Test summary metric counts sum exactly to total_transactions."""
    admin = await create_test_admin(db_session)
    course, batch = await create_test_course_and_batch(db_session, amount_inr=2500)
    ref1 = f"REF1_{uuid.uuid4().hex[:4].upper()}"
    ref2 = f"REF2_{uuid.uuid4().hex[:4].upper()}"
    ref_dup = f"REFDUP_{uuid.uuid4().hex[:4].upper()}"

    await create_test_payment_session(db_session, course, batch, ref1, status="SUBMITTED", utr="111")
    await create_test_payment_session(db_session, course, batch, ref2, status="SUBMITTED", utr="222")

    si, txs = await create_test_statement_import(
        db_session,
        admin,
        [
            {"direction": "CREDIT", "reference_id": ref1, "amount_inr": 2500, "utr": "111"},  # MATCHED
            {"direction": "CREDIT", "reference_id": ref2, "amount_inr": 2000, "utr": "222"},  # AMOUNT_MISMATCH
            {"direction": "CREDIT", "reference_id": "UNKNOWN_99", "amount_inr": 2500},        # UNKNOWN_REFERENCE
            {"direction": "CREDIT", "reference_id": "", "amount_inr": 2500},                  # NO_REFERENCE
            {"direction": "DEBIT", "reference_id": "DEBIT_1", "amount_inr": 100},            # UNMATCHED
            {"direction": "CREDIT", "reference_id": ref_dup, "amount_inr": 2500},            # DUPLICATE_TRANSACTION
            {"direction": "CREDIT", "reference_id": ref_dup, "amount_inr": 2500},            # DUPLICATE_TRANSACTION
        ],
    )

    service = ReconciliationService()
    run_res = await service.run_reconciliation(db_session, si.public_id, admin)

    sum_counts = (
        run_res.matched_count
        + run_res.amount_mismatch_count
        + run_res.unknown_reference_count
        + run_res.no_reference_count
        + run_res.utr_mismatch_count
        + run_res.duplicate_transaction_count
        + run_res.needs_review_count
        + run_res.unmatched_count
    )

    assert run_res.total_transactions == 7
    assert sum_counts == run_res.total_transactions


async def test_reconciliation_unauthenticated_api_401():
    """Test unauthenticated HTTP requests to reconciliation endpoints return 401 Unauthorized."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # POST run without auth header
        res1 = await client.post(
            "/v1/admin/reconciliation/runs",
            json={"statement_import_public_id": str(uuid.uuid4())},
        )
        assert res1.status_code == 401

        # GET runs without auth header
        res2 = await client.get("/v1/admin/reconciliation/runs")
        assert res2.status_code == 401
