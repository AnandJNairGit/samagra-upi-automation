"""Phase boundary verification test for Phase 9.

MANDATORY GUARANTEE:
Phase 9 MUST NOT alter, match, or reconcile existing PaymentSession or PaymentSubmission records.
"""

import os
import uuid
import pytest
import httpx
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth.hashing import hash_password
from app.auth.jwt import create_access_token
from app.core.database import get_db
from app.main import app
from app.models.admin_user import AdminUser
from app.models.course import Course
from app.models.batch import Batch
from app.models.payment_session import PaymentSession
from app.models.payment_submission import PaymentSubmission


@pytest.fixture(autouse=True)
def setup_test_environment(db_session: AsyncSession):
    """Bind test database session to FastAPI dependency."""
    app.dependency_overrides[get_db] = lambda: db_session
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_phase9_does_not_modify_payment_sessions_or_submissions(db_session: AsyncSession):
    """Verify Phase 9 statement import leaves PaymentSession and PaymentSubmission records 100% untouched."""

    unique_ref = f"BOUND_{uuid.uuid4().hex[:8].upper()}"
    unique_utr = f"8888{uuid.uuid4().hex[:8]}"

    # 1. Create active Admin User
    admin = AdminUser(
        public_id=uuid.uuid4(),
        email=f"boundary.admin.{uuid.uuid4().hex[:6]}@samagra.org",
        password_hash=hash_password("Password123!"),
        full_name="Boundary Admin",
        is_active=True,
    )
    db_session.add(admin)
    await db_session.flush()
    token = create_access_token(admin.public_id)

    # 2. Create active Course & Batch
    course = Course(name="Phase 9 Boundary Course", description="Test", status="ACTIVE")
    db_session.add(course)
    await db_session.flush()

    batch = Batch(
        course_id=course.id,
        name="Phase 9 Boundary Cohort",
        amount_inr=2500,
        status="ACTIVE",
    )
    db_session.add(batch)
    await db_session.flush()

    # 3. Create PaymentSession matching unique_ref
    session = PaymentSession(
        full_name="Boundary Participant",
        phone="9876543210",
        email="boundary@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot="Phase 9 Boundary Course",
        batch_name_snapshot="Phase 9 Boundary Cohort",
        amount_inr=2500,
        reference_id=unique_ref,
        upi_id_snapshot="samagralearning@ibl",
        payee_name_snapshot="Samagra Training",
        upi_uri=f"upi://pay?pa=samagralearning@ibl&pn=Samagra%20Training&am=2500&cu=INR&tn={unique_ref}&tr={unique_ref}",
        status="SUBMITTED",
    )
    db_session.add(session)
    await db_session.flush()

    # 4. Create PaymentSubmission matching unique_utr
    submission = PaymentSubmission(
        payment_session_id=session.id,
        utr=unique_utr,
        status="SUBMITTED",
        is_current=True,
    )
    db_session.add(submission)
    await db_session.commit()

    # Record pre-import snapshots
    pre_session_status = session.status
    pre_session_amount = session.amount_inr
    pre_submission_status = submission.status
    pre_submission_utr = submission.utr
    pre_submission_is_current = submission.is_current

    # Create CSV content containing matching unique_ref and unique_utr
    csv_content = f"Transaction Date,Transaction Type,Transaction Remarks,Credit Amount,UTR Number\n2026-08-16 10:30:00,CREDIT,{unique_ref},2500,{unique_utr}\n"
    csv_bytes = csv_content.encode("utf-8")

    # 5. Perform Statement Import containing unique_ref and unique_utr
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        prev_res = await client.post(
            "/v1/admin/statement-imports/preview",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("boundary_statement.csv", csv_bytes, "text/csv")},
            data={"header_row_index": "1"},
        )

        assert prev_res.status_code == 200
        preview_token = prev_res.json()["preview_token"]

        confirm_res = await client.post(
            "/v1/admin/statement-imports/confirm",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "preview_token": preview_token,
                "header_row_index": 1,
                "column_mapping": {
                    "reference_id": {"column_index": 2, "header": "Transaction Remarks"},
                    "amount": {"column_index": 3, "header": "Credit Amount"},
                    "transaction_at": {"column_index": 0, "header": "Transaction Date"},
                    "direction": {"column_index": 1, "header": "Transaction Type"},
                    "utr": {"column_index": 4, "header": "UTR Number"},
                },
            },
        )

        assert confirm_res.status_code == 200
        assert confirm_res.json()["status"] == "COMPLETED"

    # 6. Re-query PaymentSession and PaymentSubmission from DB and verify 100% UNCHANGED
    res_session = await db_session.execute(
        select(PaymentSession).where(PaymentSession.id == session.id)
    )
    post_session = res_session.scalar_one()

    res_submission = await db_session.execute(
        select(PaymentSubmission).where(PaymentSubmission.id == submission.id)
    )
    post_submission = res_submission.scalar_one()

    # VERIFY STRICT INVARIANCE
    assert post_session.status == pre_session_status == "SUBMITTED"
    assert post_session.amount_inr == pre_session_amount == 2500
    assert post_session.reference_id == unique_ref

    assert post_submission.status == pre_submission_status == "SUBMITTED"
    assert post_submission.utr == pre_submission_utr == unique_utr
    assert post_submission.is_current == pre_submission_is_current is True
    assert post_submission.reviewed_by is None
    assert post_submission.reviewed_at is None
