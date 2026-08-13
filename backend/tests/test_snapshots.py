"""Historical payment snapshot immutability verification tests."""

import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.course import Course
from app.models.batch import Batch
from app.models.payment_session import PaymentSession


@pytest.mark.asyncio
async def test_historical_payment_snapshots_remain_immutable_on_batch_updates(
    db_session: AsyncSession,
):
    """Verify that updating course name, batch name, and batch price does NOT alter payment session snapshots."""
    # 1. Create original Course & Batch
    course = Course(
        public_id=uuid.uuid4(),
        name="AI Masterclass",
        description="Original AI course",
        status="ACTIVE",
    )
    db_session.add(course)
    await db_session.flush()

    batch = Batch(
        public_id=uuid.uuid4(),
        course_id=course.id,
        name="August Batch",
        amount_inr=2000,  # Original price ₹2000
        status="ACTIVE",
    )
    db_session.add(batch)
    await db_session.flush()

    # 2. Create Payment Session capturing snapshots
    payment_session = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="John Doe",
        phone="+919876543210",
        email="john.doe@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot=course.name,
        batch_name_snapshot=batch.name,
        amount_inr=batch.amount_inr,
        reference_id=f"REF_SNAP_{uuid.uuid4().hex[:6]}",
        upi_id_snapshot="samagra@upi",
        payee_name_snapshot="Samagra Educational Society",
        upi_uri="upi://pay?pa=samagra@upi&pn=Samagra&am=2000",
        status="PENDING",
    )
    db_session.add(payment_session)
    await db_session.flush()

    # 3. Admin modifies Course and Batch afterward
    course.name = "Advanced AI Masterclass (Updated)"
    batch.name = "August Batch (Updated)"
    batch.amount_inr = 3500  # Price increased to ₹3500
    await db_session.flush()

    # 4. Refresh and assert Payment Session snapshots remain untouched
    stmt = select(PaymentSession).where(PaymentSession.id == payment_session.id)
    result = await db_session.execute(stmt)
    persisted_session = result.scalar_one()

    assert persisted_session.course_name_snapshot == "AI Masterclass"
    assert persisted_session.batch_name_snapshot == "August Batch"
    assert persisted_session.amount_inr == 2000
    assert persisted_session.upi_id_snapshot == "samagra@upi"
    assert persisted_session.payee_name_snapshot == "Samagra Educational Society"
    assert persisted_session.upi_uri == "upi://pay?pa=samagra@upi&pn=Samagra&am=2000"
