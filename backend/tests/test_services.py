"""Integration and concurrency tests for the Service layer."""

import asyncio
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings
from app.models.admin_user import AdminUser
from app.models.course import Course
from app.models.batch import Batch
from app.models.payment_session import PaymentSession
from app.models.payment_submission import PaymentSubmission
from app.services.exceptions import DuplicateUTRError, InvalidSessionStateError
from app.services.payment_submission_service import PaymentSubmissionService


@pytest.mark.asyncio
async def test_submit_utr_initial_workflow(db_session: AsyncSession):
    """Test initial UTR submission workflow from PENDING to SUBMITTED."""
    service = PaymentSubmissionService()

    course = Course(public_id=uuid.uuid4(), name="Service Course")
    db_session.add(course)
    await db_session.flush()

    batch = Batch(public_id=uuid.uuid4(), course_id=course.id, name="Service Batch", amount_inr=2000)
    db_session.add(batch)
    await db_session.flush()

    ps = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="Jane Doe",
        phone="+919876543210",
        email="jane@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot="Service Course",
        batch_name_snapshot="Service Batch",
        amount_inr=2000,
        reference_id=f"REF_SVC_{uuid.uuid4().hex[:6]}",
        upi_id_snapshot="samagra@upi",
        payee_name_snapshot="Samagra",
        upi_uri="upi://pay",
        status="PENDING",
    )
    db_session.add(ps)
    await db_session.flush()

    utr_val = f"UTR_SVC_{uuid.uuid4().hex[:8]}"
    sub = await service.submit_utr(db_session, ps.id, utr_val)

    assert sub.id is not None
    assert sub.is_current is True
    assert sub.status == "SUBMITTED"
    assert ps.status == "SUBMITTED"


@pytest.mark.asyncio
async def test_submit_utr_resubmission_after_rejection(db_session: AsyncSession):
    """Test full rejection and corrected UTR resubmission workflow."""
    service = PaymentSubmissionService()

    admin = AdminUser(
        public_id=uuid.uuid4(),
        email="admin.reviewer@samagra.org",
        password_hash="hash",
        full_name="Reviewer Admin",
    )
    course = Course(public_id=uuid.uuid4(), name="Resubmit Course")
    db_session.add_all([admin, course])
    await db_session.flush()

    batch = Batch(public_id=uuid.uuid4(), course_id=course.id, name="Resubmit Batch", amount_inr=2000)
    db_session.add(batch)
    await db_session.flush()

    ps = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="Student",
        phone="+919876543210",
        email="student@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot="Resubmit Course",
        batch_name_snapshot="Resubmit Batch",
        amount_inr=2000,
        reference_id=f"REF_RESUB_{uuid.uuid4().hex[:6]}",
        upi_id_snapshot="samagra@upi",
        payee_name_snapshot="Samagra",
        upi_uri="upi://pay",
        status="PENDING",
    )
    db_session.add(ps)
    await db_session.flush()

    # 1. Initial submission
    utr_1 = f"UTR_WRONG_{uuid.uuid4().hex[:8]}"
    sub_1 = await service.submit_utr(db_session, ps.id, utr_1)
    assert ps.status == "SUBMITTED"

    # 2. Admin rejects submission
    rejected_sub = await service.reject_submission(
        db_session, sub_1.id, admin.id, reason="Incorrect UTR provided"
    )
    assert rejected_sub.status == "REJECTED"
    assert ps.status == "REJECTED"

    # 3. User submits corrected UTR
    utr_2 = f"UTR_CORRECT_{uuid.uuid4().hex[:8]}"
    sub_2 = await service.submit_utr(db_session, ps.id, utr_2)

    assert sub_2.status == "SUBMITTED"
    assert sub_2.is_current is True
    assert sub_1.is_current is False  # previous submission deactivated
    assert ps.status == "SUBMITTED"  # session returned to SUBMITTED


@pytest.mark.asyncio
async def test_approve_submission_workflow(db_session: AsyncSession):
    """Test approve_submission workflow, timestamps, reviewer assignment, and session sync."""
    service = PaymentSubmissionService()

    admin = AdminUser(
        public_id=uuid.uuid4(),
        email="approver@samagra.org",
        password_hash="hash",
        full_name="Approver Admin",
    )
    course = Course(public_id=uuid.uuid4(), name="Approve Course")
    db_session.add_all([admin, course])
    await db_session.flush()

    batch = Batch(public_id=uuid.uuid4(), course_id=course.id, name="Approve Batch", amount_inr=2000)
    db_session.add(batch)
    await db_session.flush()

    ps = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="Alice Student",
        phone="+919876543210",
        email="alice.student@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot="Approve Course",
        batch_name_snapshot="Approve Batch",
        amount_inr=2000,
        reference_id=f"REF_APP_WF_{uuid.uuid4().hex[:6]}",
        upi_id_snapshot="samagra@upi",
        payee_name_snapshot="Samagra",
        upi_uri="upi://pay",
        status="PENDING",
    )
    db_session.add(ps)
    await db_session.flush()

    utr_val = f"UTR_APP_{uuid.uuid4().hex[:8]}"
    sub = await service.submit_utr(db_session, ps.id, utr_val)
    assert ps.status == "SUBMITTED"

    approved_sub = await service.approve_submission(db_session, sub.id, admin.id)
    assert approved_sub.status == "APPROVED"
    assert approved_sub.reviewed_by == admin.id
    assert approved_sub.reviewed_at is not None
    assert ps.status == "APPROVED"


@pytest.mark.asyncio
async def test_reject_submission_workflow(db_session: AsyncSession):
    """Test reject_submission workflow, reason recording, reviewer assignment, and session sync."""
    service = PaymentSubmissionService()

    admin = AdminUser(
        public_id=uuid.uuid4(),
        email="rejecter@samagra.org",
        password_hash="hash",
        full_name="Rejecter Admin",
    )
    course = Course(public_id=uuid.uuid4(), name="Reject Course")
    db_session.add_all([admin, course])
    await db_session.flush()

    batch = Batch(public_id=uuid.uuid4(), course_id=course.id, name="Reject Batch", amount_inr=2000)
    db_session.add(batch)
    await db_session.flush()

    ps = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="Bob Student",
        phone="+919876543210",
        email="bob.student@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot="Reject Course",
        batch_name_snapshot="Reject Batch",
        amount_inr=2000,
        reference_id=f"REF_REJ_WF_{uuid.uuid4().hex[:6]}",
        upi_id_snapshot="samagra@upi",
        payee_name_snapshot="Samagra",
        upi_uri="upi://pay",
        status="PENDING",
    )
    db_session.add(ps)
    await db_session.flush()

    utr_val = f"UTR_REJ_{uuid.uuid4().hex[:8]}"
    sub = await service.submit_utr(db_session, ps.id, utr_val)
    assert ps.status == "SUBMITTED"

    rejected_sub = await service.reject_submission(
        db_session, sub.id, admin.id, reason="Bank statement mismatch"
    )
    assert rejected_sub.status == "REJECTED"
    assert rejected_sub.reviewed_by == admin.id
    assert rejected_sub.rejection_reason == "Bank statement mismatch"
    assert rejected_sub.reviewed_at is not None
    assert ps.status == "REJECTED"


@pytest.mark.asyncio
async def test_approve_or_reject_already_processed_submission_raises_error(db_session: AsyncSession):
    """Test that approving or rejecting an already processed submission raises InvalidSessionStateError."""
    service = PaymentSubmissionService()

    admin = AdminUser(
        public_id=uuid.uuid4(),
        email="guard.admin@samagra.org",
        password_hash="hash",
        full_name="Guard Admin",
    )
    course = Course(public_id=uuid.uuid4(), name="Guard Course")
    db_session.add_all([admin, course])
    await db_session.flush()

    batch = Batch(public_id=uuid.uuid4(), course_id=course.id, name="Guard Batch", amount_inr=2000)
    db_session.add(batch)
    await db_session.flush()

    ps = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="Guard Student",
        phone="+919876543210",
        email="guard@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot="Guard Course",
        batch_name_snapshot="Guard Batch",
        amount_inr=2000,
        reference_id=f"REF_GUARD_{uuid.uuid4().hex[:6]}",
        upi_id_snapshot="samagra@upi",
        payee_name_snapshot="Samagra",
        upi_uri="upi://pay",
        status="PENDING",
    )
    db_session.add(ps)
    await db_session.flush()

    sub = await service.submit_utr(db_session, ps.id, f"UTR_GUARD_{uuid.uuid4().hex[:8]}")
    await service.approve_submission(db_session, sub.id, admin.id)

    # Attempting to approve again -> InvalidSessionStateError
    with pytest.raises(InvalidSessionStateError):
        await service.approve_submission(db_session, sub.id, admin.id)

    # Attempting to reject an approved submission -> InvalidSessionStateError
    with pytest.raises(InvalidSessionStateError):
        await service.reject_submission(db_session, sub.id, admin.id, reason="Too late")


@pytest.mark.asyncio
async def test_duplicate_utr_raises_domain_exception(db_session: AsyncSession):
    """Test that duplicate UTR submissions translate to DuplicateUTRError domain exception."""
    service = PaymentSubmissionService()

    course = Course(public_id=uuid.uuid4(), name="Dup UTR Course")
    db_session.add(course)
    await db_session.flush()

    batch = Batch(public_id=uuid.uuid4(), course_id=course.id, name="Dup UTR Batch", amount_inr=1000)
    db_session.add(batch)
    await db_session.flush()

    ps1 = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="User 1",
        phone="+919876543210",
        email="u1@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot="Dup UTR Course",
        batch_name_snapshot="Dup UTR Batch",
        amount_inr=1000,
        reference_id=f"REF_DUP1_{uuid.uuid4().hex[:6]}",
        upi_id_snapshot="samagra@upi",
        payee_name_snapshot="Samagra",
        upi_uri="upi://pay",
        status="PENDING",
    )
    ps2 = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="User 2",
        phone="+919876543212",
        email="u2@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot="Dup UTR Course",
        batch_name_snapshot="Dup UTR Batch",
        amount_inr=1000,
        reference_id=f"REF_DUP2_{uuid.uuid4().hex[:6]}",
        upi_id_snapshot="samagra@upi",
        payee_name_snapshot="Samagra",
        upi_uri="upi://pay",
        status="PENDING",
    )
    db_session.add_all([ps1, ps2])
    await db_session.flush()

    shared_utr = f"UTR_COLLIDE_{uuid.uuid4().hex[:8]}"
    await service.submit_utr(db_session, ps1.id, shared_utr)

    # Submitting same UTR for ps2 should raise DuplicateUTRError
    with pytest.raises(DuplicateUTRError):
        await service.submit_utr(db_session, ps2.id, shared_utr)


@pytest.mark.asyncio
async def test_invalid_session_state_submission_rejected(db_session: AsyncSession):
    """Test that submitting UTR to an APPROVED session raises InvalidSessionStateError."""
    service = PaymentSubmissionService()

    course = Course(public_id=uuid.uuid4(), name="State Course")
    db_session.add(course)
    await db_session.flush()

    batch = Batch(public_id=uuid.uuid4(), course_id=course.id, name="State Batch", amount_inr=1000)
    db_session.add(batch)
    await db_session.flush()

    ps = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="User Approved",
        phone="+919876543210",
        email="uapp@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot="State Course",
        batch_name_snapshot="State Batch",
        amount_inr=1000,
        reference_id=f"REF_APP_{uuid.uuid4().hex[:6]}",
        upi_id_snapshot="samagra@upi",
        payee_name_snapshot="Samagra",
        upi_uri="upi://pay",
        status="APPROVED",  # Already approved
    )
    db_session.add(ps)
    await db_session.flush()

    with pytest.raises(InvalidSessionStateError):
        await service.submit_utr(db_session, ps.id, f"UTR_{uuid.uuid4().hex[:8]}")


@pytest.mark.asyncio
async def test_concurrent_utr_submissions_row_locking():
    """Live concurrency test: two simultaneous submit_utr requests on separate DB sessions.

    Verifies row locking serializes execution, ensures exactly one is_current=True record,
    and prevents inconsistent states.
    """
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    service = PaymentSubmissionService()
    session_id = None

    # Setup test session in DB
    async with session_factory() as setup_session:
        course = Course(public_id=uuid.uuid4(), name="Concurrency Course")
        setup_session.add(course)
        await setup_session.flush()

        batch = Batch(public_id=uuid.uuid4(), course_id=course.id, name="Concurrency Batch", amount_inr=2000)
        setup_session.add(batch)
        await setup_session.flush()

        ps = PaymentSession(
            public_id=uuid.uuid4(),
            full_name="Concurrent User",
            phone="+919876543210",
            email="concurrent@example.com",
            course_id=course.id,
            batch_id=batch.id,
            course_name_snapshot="Concurrency Course",
            batch_name_snapshot="Concurrency Batch",
            amount_inr=2000,
            reference_id=f"REF_CONC_{uuid.uuid4().hex[:6]}",
            upi_id_snapshot="samagra@upi",
            payee_name_snapshot="Samagra",
            upi_uri="upi://pay",
            status="PENDING",
        )
        setup_session.add(ps)
        await setup_session.commit()
        session_id = ps.id

    # Concurrent worker task
    async def worker_submit(utr_val: str):
        async with session_factory() as session:
            try:
                await service.submit_utr(session, session_id, utr_val)
                await session.commit()
                return "SUCCESS"
            except Exception as e:
                await session.rollback()
                return f"ERROR: {type(e).__name__}"

    utr_a = f"UTR_CONC_A_{uuid.uuid4().hex[:8]}"
    utr_b = f"UTR_CONC_B_{uuid.uuid4().hex[:8]}"

    # Run simultaneously
    results = await asyncio.gather(
        worker_submit(utr_a),
        worker_submit(utr_b),
        return_exceptions=False,
    )

    # Verify final state in database
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

        # Cleanup test data in dependency order
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


@pytest.mark.asyncio
async def test_concurrent_approval_rejection_row_locking():
    """Live concurrency test: simultaneous approve and reject requests on the same submission.

    Verifies row locking on submission and payment session serializes execution:
    one operation succeeds and the competing operation receives InvalidSessionStateError,
    preventing state corruption.
    """
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    service = PaymentSubmissionService()
    submission_id = None
    session_id = None
    admin1_id = None
    admin2_id = None

    # Setup test data in DB
    async with session_factory() as setup_session:
        admin1 = AdminUser(
            public_id=uuid.uuid4(),
            email=f"admin1_{uuid.uuid4().hex[:6]}@samagra.org",
            password_hash="hash",
            full_name="Admin One",
        )
        admin2 = AdminUser(
            public_id=uuid.uuid4(),
            email=f"admin2_{uuid.uuid4().hex[:6]}@samagra.org",
            password_hash="hash",
            full_name="Admin Two",
        )
        course = Course(public_id=uuid.uuid4(), name="Race Course")
        setup_session.add_all([admin1, admin2, course])
        await setup_session.flush()

        batch = Batch(public_id=uuid.uuid4(), course_id=course.id, name="Race Batch", amount_inr=2000)
        setup_session.add(batch)
        await setup_session.flush()

        ps = PaymentSession(
            public_id=uuid.uuid4(),
            full_name="Race User",
            phone="+919876543210",
            email="race@example.com",
            course_id=course.id,
            batch_id=batch.id,
            course_name_snapshot="Race Course",
            batch_name_snapshot="Race Batch",
            amount_inr=2000,
            reference_id=f"REF_RACE_{uuid.uuid4().hex[:6]}",
            upi_id_snapshot="samagra@upi",
            payee_name_snapshot="Samagra",
            upi_uri="upi://pay",
            status="PENDING",
        )
        setup_session.add(ps)
        await setup_session.flush()

        sub = await service.submit_utr(setup_session, ps.id, f"UTR_RACE_{uuid.uuid4().hex[:8]}")
        await setup_session.commit()

        submission_id = sub.id
        session_id = ps.id
        admin1_id = admin1.id
        admin2_id = admin2.id

    # Worker 1: Approve
    async def worker_approve():
        async with session_factory() as session:
            try:
                await service.approve_submission(session, submission_id, admin1_id)
                await session.commit()
                return "APPROVED"
            except Exception as e:
                await session.rollback()
                return f"ERROR: {type(e).__name__}"

    # Worker 2: Reject
    async def worker_reject():
        async with session_factory() as session:
            try:
                await service.reject_submission(session, submission_id, admin2_id, reason="Conflicting review")
                await session.commit()
                return "REJECTED"
            except Exception as e:
                await session.rollback()
                return f"ERROR: {type(e).__name__}"

    # Run simultaneously
    results = await asyncio.gather(
        worker_approve(),
        worker_reject(),
        return_exceptions=False,
    )

    # One should succeed, one should receive InvalidSessionStateError
    success_results = [r for r in results if r in ("APPROVED", "REJECTED")]
    error_results = [r for r in results if r.startswith("ERROR: InvalidSessionStateError")]

    assert len(success_results) == 1, f"Exactly one review action must succeed: {results}"
    assert len(error_results) == 1, f"Compete review action must receive InvalidSessionStateError: {results}"

    # Verify consistent database state
    async with session_factory() as verify_session:
        final_sub = await verify_session.get(PaymentSubmission, submission_id)
        final_ps = await verify_session.get(PaymentSession, session_id)

        assert final_sub.status in ("APPROVED", "REJECTED")
        assert final_ps.status == final_sub.status, "Session status must match submission status."

        # Cleanup
        await verify_session.delete(final_sub)
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

        admin1_to_delete = await verify_session.get(AdminUser, admin1_id)
        if admin1_to_delete:
            await verify_session.delete(admin1_to_delete)
        admin2_to_delete = await verify_session.get(AdminUser, admin2_id)
        if admin2_to_delete:
            await verify_session.delete(admin2_to_delete)
        await verify_session.commit()

    await engine.dispose()
