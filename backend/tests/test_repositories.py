"""Unit tests for pure persistence repository implementations."""

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.admin_user import AdminUser
from app.models.course import Course
from app.models.batch import Batch
from app.models.payment_session import PaymentSession
from app.models.payment_submission import PaymentSubmission
from app.repositories.admin_user_repository import AdminUserRepository
from app.repositories.course_repository import CourseRepository
from app.repositories.batch_repository import BatchRepository
from app.repositories.payment_session_repository import PaymentSessionRepository
from app.repositories.payment_submission_repository import PaymentSubmissionRepository


@pytest.mark.asyncio
async def test_admin_user_repository_crud(db_session: AsyncSession):
    """Test AdminUserRepository get_by_id, get_by_email, create, update."""
    repo = AdminUserRepository()
    pub_id = uuid.uuid4()
    user = AdminUser(
        public_id=pub_id,
        email="repo.admin@samagra.org",
        password_hash="pwd_hash",
        full_name="Repo Admin",
    )
    created = await repo.create(db_session, user)
    assert created.id is not None

    by_id = await repo.get_by_id(db_session, created.id)
    assert by_id is not None
    assert by_id.email == "repo.admin@samagra.org"

    by_pub = await repo.get_by_public_id(db_session, pub_id)
    assert by_pub is not None
    assert by_pub.id == created.id

    by_email = await repo.get_by_email(db_session, "REPO.ADMIN@SAMAGRA.ORG")
    assert by_email is not None
    assert by_email.id == created.id


@pytest.mark.asyncio
async def test_course_and_batch_repositories(db_session: AsyncSession):
    """Test CourseRepository and BatchRepository persistence queries."""
    course_repo = CourseRepository()
    batch_repo = BatchRepository()

    course = Course(public_id=uuid.uuid4(), name="Repo Course", status="ACTIVE")
    await course_repo.create(db_session, course)

    batch = Batch(
        public_id=uuid.uuid4(),
        course_id=course.id,
        name="Repo Batch",
        amount_inr=3000,
        status="ACTIVE",
    )
    await batch_repo.create(db_session, batch)

    courses = await course_repo.list_all(db_session, status="ACTIVE")
    assert any(c.id == course.id for c in courses)

    batches = await batch_repo.list_by_course_id(db_session, course.id)
    assert len(batches) == 1
    assert batches[0].amount_inr == 3000


@pytest.mark.asyncio
async def test_payment_session_and_submission_repositories(db_session: AsyncSession):
    """Test PaymentSessionRepository and PaymentSubmissionRepository persistence."""
    course_repo = CourseRepository()
    batch_repo = BatchRepository()
    session_repo = PaymentSessionRepository()
    sub_repo = PaymentSubmissionRepository()

    course = await course_repo.create(
        db_session, Course(public_id=uuid.uuid4(), name="PS Course")
    )
    batch = await batch_repo.create(
        db_session,
        Batch(public_id=uuid.uuid4(), course_id=course.id, name="PS Batch", amount_inr=1000),
    )

    ref_id = f"REF_REPO_{uuid.uuid4().hex[:6]}"
    ps = await session_repo.create(
        db_session,
        PaymentSession(
            public_id=uuid.uuid4(),
            full_name="Student",
            phone="+919876543210",
            email="student@example.com",
            course_id=course.id,
            batch_id=batch.id,
            course_name_snapshot="PS Course",
            batch_name_snapshot="PS Batch",
            amount_inr=1000,
            reference_id=ref_id,
            upi_id_snapshot="samagra@upi",
            payee_name_snapshot="Samagra",
            upi_uri="upi://pay",
        ),
    )

    by_ref = await session_repo.get_by_reference_id(db_session, ref_id)
    assert by_ref is not None
    assert by_ref.id == ps.id

    utr_val = f"UTR_REPO_{uuid.uuid4().hex[:8]}"
    sub = await sub_repo.create(
        db_session,
        PaymentSubmission(
            public_id=uuid.uuid4(),
            payment_session_id=ps.id,
            utr=utr_val,
            status="SUBMITTED",
            is_current=True,
        ),
    )

    current_sub = await sub_repo.get_current_for_session(db_session, ps.id)
    assert current_sub is not None
    assert current_sub.utr == utr_val

    # Test deactivate current
    deactivated_count = await sub_repo.deactivate_current_for_session(db_session, ps.id)
    assert deactivated_count == 1
    after_deactivate = await sub_repo.get_current_for_session(db_session, ps.id)
    assert after_deactivate is None
