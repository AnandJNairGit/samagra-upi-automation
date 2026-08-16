"""Test verifying historical payment session snapshot immutability during Phase 4 course & batch modifications."""

import uuid
from datetime import datetime, timezone
import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import select
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
        full_name="Snapshot Invariance Admin",
        is_active=True,
    )
    db.add(admin)
    await db.flush()
    token = create_access_token(admin.public_id)
    return admin, token


@pytest.mark.asyncio
async def test_payment_session_snapshots_immutable_on_course_and_batch_updates(db_session: AsyncSession):
    """Verify modifying course name and batch amount in Phase 4 leaves historical payment_sessions snapshots intact."""
    _, token = await create_test_admin(db_session)

    # 1. Create original Course & Batch
    course = Course(
        public_id=uuid.uuid4(),
        name="Original AI Masterclass",
        description="Original syllabus",
        status="ACTIVE",
    )
    db_session.add(course)
    await db_session.flush()

    batch = Batch(
        public_id=uuid.uuid4(),
        course_id=course.id,
        name="August 2026 Cohort",
        amount_inr=1500,  # Original fee ₹1,500
        status="ACTIVE",
        starts_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        ends_at=datetime(2026, 8, 31, tzinfo=timezone.utc),
    )
    db_session.add(batch)
    await db_session.flush()

    # 2. Generate PaymentSession with snapshot values
    ref_id = f"REF_{uuid.uuid4().hex[:8].upper()}"
    original_uri = "upi://pay?pa=samagra@upi&pn=Samagra%20Edu&am=1500"
    payment_session = PaymentSession(
        public_id=uuid.uuid4(),
        full_name="John Doe",
        phone="+919876543210",
        email="john@example.com",
        course_id=course.id,
        batch_id=batch.id,
        course_name_snapshot="Original AI Masterclass",
        batch_name_snapshot="August 2026 Cohort",
        amount_inr=1500,
        reference_id=ref_id,
        upi_id_snapshot="samagra@upi",
        payee_name_snapshot="Samagra Edu",
        upi_uri=original_uri,
        status="PENDING",
    )
    db_session.add(payment_session)
    await db_session.flush()
    session_id = payment_session.id

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 3. Admin updates course name via API
        patch_course_res = await client.patch(
            f"/v1/admin/courses/{course.public_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={"name": "Modified AI Masterclass PRO"},
        )
        assert patch_course_res.status_code == 200

        # 4. Admin updates batch name and fee from ₹1,500 to ₹3,500 via API
        patch_batch_res = await client.patch(
            f"/v1/admin/batches/{batch.public_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "name": "August 2026 Cohort Extended",
                "amount_inr": 3500,
            },
        )
        assert patch_batch_res.status_code == 200

    # 5. Reload PaymentSession from database and assert snapshots remain completely unchanged
    stmt = select(PaymentSession).where(PaymentSession.id == session_id)
    result = await db_session.execute(stmt)
    reloaded_session = result.scalar_one()

    assert reloaded_session.course_name_snapshot == "Original AI Masterclass"
    assert reloaded_session.batch_name_snapshot == "August 2026 Cohort"
    assert reloaded_session.amount_inr == 1500
    assert reloaded_session.upi_uri == original_uri
    assert reloaded_session.reference_id == ref_id
    assert reloaded_session.status == "PENDING"
