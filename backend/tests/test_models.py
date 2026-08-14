"""Unit tests for SQLAlchemy domain models."""

import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.admin_user import AdminUser
from app.models.course import Course
from app.models.batch import Batch
from app.models.payment_session import PaymentSession
from app.models.payment_submission import PaymentSubmission


@pytest.mark.asyncio
async def test_admin_user_model_creation(db_session: AsyncSession):
    """Verify AdminUser model attributes, defaults, and public UUID."""
    user = AdminUser(
        public_id=uuid.uuid4(),
        email="test.admin@example.com",
        password_hash="hashed_secret",
        full_name="Test Administrator",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    assert user.id is not None
    assert isinstance(user.public_id, uuid.UUID)
    assert user.is_active is True
    assert user.created_at is not None
    assert user.updated_at is not None


@pytest.mark.asyncio
async def test_course_and_batch_models_relationship(db_session: AsyncSession):
    """Verify Course and Batch relationship and whole-rupee amount representation."""
    course = Course(
        public_id=uuid.uuid4(),
        name="AI for Engineers",
        description="Applied machine learning curriculum.",
        status="ACTIVE",
    )
    db_session.add(course)
    await db_session.flush()

    batch = Batch(
        public_id=uuid.uuid4(),
        course_id=course.id,
        name="Cohort 1",
        amount_inr=5000,  # ₹5,000 whole rupees
        status="ACTIVE",
        starts_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        ends_at=datetime(2026, 9, 30, tzinfo=timezone.utc),
    )
    db_session.add(batch)
    await db_session.flush()

    assert batch.id is not None
    assert batch.amount_inr == 5000
    assert batch.course_id == course.id


@pytest.mark.asyncio
async def test_payment_session_and_submission_models(db_session: AsyncSession):
    """Verify PaymentSession snapshots and PaymentSubmission relationship."""
    # 1. Create course and batch
    course = Course(
        public_id=uuid.uuid4(),
        name="Prompt Engineering",
        status="ACTIVE",
    )
    db_session.add(course)
    await db_session.flush()

    batch = Batch(
        public_id=uuid.uuid4(),
        course_id=course.id,
        name="Weekend Batch",
        amount_inr=1500,
        status="ACTIVE",
    )
    db_session.add(batch)
    await db_session.flush()

    # 2. Create payment session
    ref_id = f"REF_{uuid.uuid4().hex[:8].upper()}"
    session_record = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="Alice Walker",
        phone="+919876543210",
        email="alice@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot="Prompt Engineering",
        batch_name_snapshot="Weekend Batch",
        amount_inr=1500,
        reference_id=ref_id,
        upi_id_snapshot="samagra@upi",
        payee_name_snapshot="Samagra Training",
        upi_uri="upi://pay?pa=samagra@upi&pn=Samagra%20Training&am=1500",
        status="PENDING",
    )
    db_session.add(session_record)
    await db_session.flush()

    assert session_record.id is not None
    assert session_record.amount_inr == 1500
    assert session_record.status == "PENDING"

    # 3. Create payment submission
    utr_val = f"UTR_{uuid.uuid4().hex[:12].upper()}"
    submission = PaymentSubmission(
        public_id=uuid.uuid4(),
        payment_session_id=session_record.id,
        utr=utr_val,
        status="SUBMITTED",
        is_current=True,
    )
    db_session.add(submission)
    await db_session.flush()

    assert submission.id is not None
    assert submission.is_current is True
    assert submission.payment_session_id == session_record.id


@pytest.mark.asyncio
async def test_admin_session_model_creation(db_session: AsyncSession):
    """Verify AdminSession model creation, defaults, and AdminUser relationship."""
    from app.models.admin_session import AdminSession

    user = AdminUser(
        public_id=uuid.uuid4(),
        email="session.model.test@example.com",
        password_hash="hashed_secret",
        full_name="Session Model Admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    expires = datetime(2026, 12, 31, tzinfo=timezone.utc)
    admin_session = AdminSession(
        public_id=uuid.uuid4(),
        admin_user_id=user.id,
        refresh_token_hash="a" * 64,
        user_agent="Mozilla/5.0 Test",
        ip_address="192.168.1.1",
        expires_at=expires,
    )
    db_session.add(admin_session)
    await db_session.flush()

    assert admin_session.id is not None
    assert isinstance(admin_session.public_id, uuid.UUID)
    assert admin_session.admin_user_id == user.id
    assert admin_session.refresh_token_hash == "a" * 64
    assert admin_session.created_at is not None
    assert admin_session.last_used_at is not None
    assert admin_session.revoked_at is None
    assert admin_session.admin_user.email == "session.model.test@example.com"
