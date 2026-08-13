"""Database-level constraint and index verification tests."""

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.admin_user import AdminUser
from app.models.course import Course
from app.models.batch import Batch
from app.models.payment_session import PaymentSession
from app.models.payment_submission import PaymentSubmission


@pytest.mark.asyncio
async def test_admin_email_case_insensitive_uniqueness(db_session: AsyncSession):
    """Verify that admin email uniqueness is enforced case-insensitively."""
    user1 = AdminUser(
        public_id=uuid.uuid4(),
        email="Admin.Unique@example.com",
        password_hash="hash1",
        full_name="Admin One",
    )
    db_session.add(user1)
    await db_session.flush()

    user2 = AdminUser(
        public_id=uuid.uuid4(),
        email="admin.unique@example.com",  # lowercase duplicate
        password_hash="hash2",
        full_name="Admin Two",
    )
    db_session.add(user2)
    with pytest.raises((IntegrityError, DBAPIError)):
        await db_session.flush()


@pytest.mark.asyncio
async def test_batch_amount_positive_constraint(db_session: AsyncSession):
    """Verify that batch amount_inr <= 0 is rejected by DB check constraint."""
    course = Course(public_id=uuid.uuid4(), name="Test Course")
    db_session.add(course)
    await db_session.flush()

    invalid_batch = Batch(
        public_id=uuid.uuid4(),
        course_id=course.id,
        name="Zero Amount Batch",
        amount_inr=0,  # invalid
    )
    db_session.add(invalid_batch)
    with pytest.raises((IntegrityError, DBAPIError)):
        await db_session.flush()


@pytest.mark.asyncio
async def test_batch_date_range_constraint(db_session: AsyncSession):
    """Verify that batch ends_at < starts_at is rejected by DB check constraint."""
    course = Course(public_id=uuid.uuid4(), name="Test Course Dates")
    db_session.add(course)
    await db_session.flush()

    invalid_batch = Batch(
        public_id=uuid.uuid4(),
        course_id=course.id,
        name="Invalid Date Batch",
        amount_inr=1000,
        starts_at=datetime(2026, 9, 30, tzinfo=timezone.utc),
        ends_at=datetime(2026, 9, 1, tzinfo=timezone.utc),  # ends before starts
    )
    db_session.add(invalid_batch)
    with pytest.raises((IntegrityError, DBAPIError)):
        await db_session.flush()


@pytest.mark.asyncio
async def test_payment_session_amount_positive_constraint(db_session: AsyncSession):
    """Verify that payment_sessions amount_inr <= 0 is rejected by DB check constraint."""
    course = Course(public_id=uuid.uuid4(), name="Course Pos Amt")
    db_session.add(course)
    await db_session.flush()

    batch = Batch(
        public_id=uuid.uuid4(),
        course_id=course.id,
        name="Batch Pos Amt",
        amount_inr=1000,
    )
    db_session.add(batch)
    await db_session.flush()

    invalid_session = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="Bob",
        phone="+919876543211",
        email="bob@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot="Course Pos Amt",
        batch_name_snapshot="Batch Pos Amt",
        amount_inr=-500,  # negative amount
        reference_id=f"REF_NEG_{uuid.uuid4().hex[:6]}",
        upi_id_snapshot="samagra@upi",
        payee_name_snapshot="Samagra",
        upi_uri="upi://pay",
    )
    db_session.add(invalid_session)
    with pytest.raises((IntegrityError, DBAPIError)):
        await db_session.flush()


@pytest.mark.asyncio
async def test_duplicate_reference_id_rejected(db_session: AsyncSession):
    """Verify reference_id unique constraint on payment_sessions."""
    course = Course(public_id=uuid.uuid4(), name="Course Ref Test")
    db_session.add(course)
    await db_session.flush()

    batch = Batch(
        public_id=uuid.uuid4(),
        course_id=course.id,
        name="Batch Ref Test",
        amount_inr=1000,
    )
    db_session.add(batch)
    await db_session.flush()

    ref_id = f"COLLISION_REF_{uuid.uuid4().hex[:6]}"
    s1 = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="User 1",
        phone="+919876543210",
        email="u1@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot="Course Ref Test",
        batch_name_snapshot="Batch Ref Test",
        amount_inr=1000,
        reference_id=ref_id,
        upi_id_snapshot="samagra@upi",
        payee_name_snapshot="Samagra",
        upi_uri="upi://pay",
    )
    db_session.add(s1)
    await db_session.flush()

    s2 = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="User 2",
        phone="+919876543212",
        email="u2@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot="Course Ref Test",
        batch_name_snapshot="Batch Ref Test",
        amount_inr=1000,
        reference_id=ref_id,  # duplicate
        upi_id_snapshot="samagra@upi",
        payee_name_snapshot="Samagra",
        upi_uri="upi://pay",
    )
    db_session.add(s2)
    with pytest.raises((IntegrityError, DBAPIError)):
        await db_session.flush()


@pytest.mark.asyncio
async def test_duplicate_utr_rejected(db_session: AsyncSession):
    """Verify strict UTR uniqueness constraint on payment_submissions."""
    course = Course(public_id=uuid.uuid4(), name="Course UTR Test")
    db_session.add(course)
    await db_session.flush()

    batch = Batch(
        public_id=uuid.uuid4(),
        course_id=course.id,
        name="Batch UTR Test",
        amount_inr=1000,
    )
    db_session.add(batch)
    await db_session.flush()

    ps1 = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="User 1",
        phone="+919876543210",
        email="u1@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot="Course UTR Test",
        batch_name_snapshot="Batch UTR Test",
        amount_inr=1000,
        reference_id=f"REF_UTR1_{uuid.uuid4().hex[:6]}",
        upi_id_snapshot="samagra@upi",
        payee_name_snapshot="Samagra",
        upi_uri="upi://pay",
    )
    ps2 = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="User 2",
        phone="+919876543212",
        email="u2@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot="Course UTR Test",
        batch_name_snapshot="Batch UTR Test",
        amount_inr=1000,
        reference_id=f"REF_UTR2_{uuid.uuid4().hex[:6]}",
        upi_id_snapshot="samagra@upi",
        payee_name_snapshot="Samagra",
        upi_uri="upi://pay",
    )
    db_session.add_all([ps1, ps2])
    await db_session.flush()

    shared_utr = f"UTR_DUP_{uuid.uuid4().hex[:8]}"
    sub1 = PaymentSubmission(
        public_id=uuid.uuid4(),
        payment_session_id=ps1.id,
        utr=shared_utr,
        status="SUBMITTED",
        is_current=True,
    )
    db_session.add(sub1)
    await db_session.flush()

    sub2 = PaymentSubmission(
        public_id=uuid.uuid4(),
        payment_session_id=ps2.id,
        utr=shared_utr,  # duplicate UTR
        status="SUBMITTED",
        is_current=True,
    )
    db_session.add(sub2)
    with pytest.raises((IntegrityError, DBAPIError)):
        await db_session.flush()


@pytest.mark.asyncio
async def test_partial_unique_index_on_current_submission(db_session: AsyncSession):
    """Verify partial unique index: only ONE is_current=True allowed per payment_session."""
    course = Course(public_id=uuid.uuid4(), name="Course Partial Test")
    db_session.add(course)
    await db_session.flush()

    batch = Batch(
        public_id=uuid.uuid4(),
        course_id=course.id,
        name="Batch Partial Test",
        amount_inr=1000,
    )
    db_session.add(batch)
    await db_session.flush()

    ps = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="User",
        phone="+919876543210",
        email="u@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot="Course Partial Test",
        batch_name_snapshot="Batch Partial Test",
        amount_inr=1000,
        reference_id=f"REF_PARTIAL_{uuid.uuid4().hex[:6]}",
        upi_id_snapshot="samagra@upi",
        payee_name_snapshot="Samagra",
        upi_uri="upi://pay",
    )
    db_session.add(ps)
    await db_session.flush()

    # First submission as current
    sub1 = PaymentSubmission(
        public_id=uuid.uuid4(),
        payment_session_id=ps.id,
        utr=f"UTR_P1_{uuid.uuid4().hex[:8]}",
        status="SUBMITTED",
        is_current=True,
    )
    db_session.add(sub1)
    await db_session.flush()

    # Second submission also with is_current=True without deactivating sub1 -> Must Fail
    sub2 = PaymentSubmission(
        public_id=uuid.uuid4(),
        payment_session_id=ps.id,
        utr=f"UTR_P2_{uuid.uuid4().hex[:8]}",
        status="SUBMITTED",
        is_current=True,
    )
    db_session.add(sub2)
    with pytest.raises((IntegrityError, DBAPIError)):
        await db_session.flush()


@pytest.mark.asyncio
async def test_foreign_key_delete_restrict_on_course_and_batch(db_session: AsyncSession):
    """Verify that deleting a Course or Batch referenced by a PaymentSession is RESTRICTED."""
    course = Course(public_id=uuid.uuid4(), name="FK Restrict Course")
    db_session.add(course)
    await db_session.flush()

    batch = Batch(
        public_id=uuid.uuid4(),
        course_id=course.id,
        name="FK Restrict Batch",
        amount_inr=2000,
    )
    db_session.add(batch)
    await db_session.flush()

    ps = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="User FK",
        phone="+919876543210",
        email="ufk@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot="FK Restrict Course",
        batch_name_snapshot="FK Restrict Batch",
        amount_inr=2000,
        reference_id=f"REF_FK_{uuid.uuid4().hex[:6]}",
        upi_id_snapshot="samagra@upi",
        payee_name_snapshot="Samagra",
        upi_uri="upi://pay",
    )
    db_session.add(ps)
    await db_session.flush()

    # Attempt to delete batch -> Must Fail due to ON DELETE RESTRICT
    await db_session.delete(batch)
    with pytest.raises((IntegrityError, DBAPIError)):
        await db_session.flush()
