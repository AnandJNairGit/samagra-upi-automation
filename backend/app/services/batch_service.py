"""Batch service managing lifecycle, validations, concurrency locking, and business logic."""

import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.batch import Batch
from app.repositories.batch_repository import BatchRepository
from app.repositories.course_repository import CourseRepository
from app.schemas.batch import BatchCreate, BatchResponse, BatchUpdate
from app.services.exceptions import (
    BatchArchivedError,
    BatchCourseImmutableError,
    BatchNotFoundError,
    CourseArchivedError,
    CourseNotFoundError,
    InvalidAmountError,
    InvalidDateRangeError,
    InvalidStateTransitionError,
)


class BatchService:
    """Business logic and lifecycle management for batches / cohorts."""

    def __init__(
        self,
        batch_repo: Optional[BatchRepository] = None,
        course_repo: Optional[CourseRepository] = None,
    ):
        self.batch_repo = batch_repo or BatchRepository()
        self.course_repo = course_repo or CourseRepository()

    async def create_batch(
        self, db: AsyncSession, data: BatchCreate
    ) -> BatchResponse:
        """Create a new batch under an active or inactive course (archived course forbidden)."""
        # 1. Lock and verify parent course exists and is not ARCHIVED
        course = await self.course_repo.get_by_public_id_for_update(
            db, data.course_public_id
        )
        if not course:
            raise CourseNotFoundError(str(data.course_public_id))

        if course.status == "ARCHIVED":
            raise CourseArchivedError("Cannot create a batch under an archived course.")

        # 2. Validate clean name
        clean_name = data.name.strip()
        if not clean_name:
            raise ValueError("Batch name cannot be empty or whitespace only.")

        # 3. Validate creation status (ACTIVE or INACTIVE only)
        clean_status = data.status.upper().strip()
        if clean_status not in ("ACTIVE", "INACTIVE"):
            raise InvalidStateTransitionError("batch", "NONE", clean_status)

        # 4. Validate amount (must be positive whole INR)
        if data.amount_inr <= 0:
            raise InvalidAmountError()

        # 5. Validate date range
        if data.starts_at and data.ends_at and data.ends_at < data.starts_at:
            raise InvalidDateRangeError()

        batch = Batch(
            public_id=uuid.uuid4(),
            course_id=course.id,
            name=clean_name,
            amount_inr=data.amount_inr,
            status=clean_status,
            starts_at=data.starts_at,
            ends_at=data.ends_at,
        )
        await self.batch_repo.create(db, batch)
        batch.course = course

        return BatchResponse(
            public_id=batch.public_id,
            course_public_id=course.public_id,
            course_name=course.name,
            name=batch.name,
            amount_inr=batch.amount_inr,
            status=batch.status,
            starts_at=batch.starts_at,
            ends_at=batch.ends_at,
            created_at=batch.created_at,
            updated_at=batch.updated_at,
        )

    async def get_batch(
        self, db: AsyncSession, public_id: uuid.UUID
    ) -> BatchResponse:
        """Retrieve a batch by public UUID with parent course details."""
        batch = await self.batch_repo.get_by_public_id_with_course(db, public_id)
        if not batch:
            raise BatchNotFoundError(str(public_id))

        return BatchResponse(
            public_id=batch.public_id,
            course_public_id=batch.course.public_id if batch.course else uuid.UUID(int=0),
            course_name=batch.course.name if batch.course else None,
            name=batch.name,
            amount_inr=batch.amount_inr,
            status=batch.status,
            starts_at=batch.starts_at,
            ends_at=batch.ends_at,
            created_at=batch.created_at,
            updated_at=batch.updated_at,
        )

    async def list_batches(
        self,
        db: AsyncSession,
        course_public_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
    ) -> List[BatchResponse]:
        """List batches with course details, optionally filtered by course UUID and/or status."""
        filter_status = status.upper().strip() if status else None
        if filter_status and filter_status not in ("ACTIVE", "INACTIVE", "ARCHIVED"):
            raise ValueError("Status filter must be 'ACTIVE', 'INACTIVE', or 'ARCHIVED'.")

        course_id: Optional[int] = None
        if course_public_id is not None:
            course = await self.course_repo.get_by_public_id(db, course_public_id)
            if not course:
                raise CourseNotFoundError(str(course_public_id))
            course_id = course.id

        batches = await self.batch_repo.list_all_with_course(
            db, course_id=course_id, status=filter_status
        )

        return [
            BatchResponse(
                public_id=b.public_id,
                course_public_id=b.course.public_id if b.course else uuid.UUID(int=0),
                course_name=b.course.name if b.course else None,
                name=b.name,
                amount_inr=b.amount_inr,
                status=b.status,
                starts_at=b.starts_at,
                ends_at=b.ends_at,
                created_at=b.created_at,
                updated_at=b.updated_at,
            )
            for b in batches
        ]

    async def update_batch(
        self, db: AsyncSession, public_id: uuid.UUID, data: BatchUpdate
    ) -> BatchResponse:
        """Update a batch enforcing strict lifecycle, payment session immutability, and concurrency locks."""
        # 1. Lock batch row
        batch = await self.batch_repo.get_by_public_id_for_update(db, public_id)
        if not batch:
            raise BatchNotFoundError(str(public_id))

        # 2. Check if batch is currently ARCHIVED -> ARCHIVED is terminal & strictly read-only
        if batch.status == "ARCHIVED":
            raise BatchArchivedError("Batch is archived and cannot be modified.")

        # 3. Handle course reassignment if requested
        if data.course_public_id is not None:
            target_course = await self.course_repo.get_by_public_id_for_update(
                db, data.course_public_id
            )
            if not target_course:
                raise CourseNotFoundError(str(data.course_public_id))

            if target_course.id != batch.course_id:
                # Concurrency-safe check: verify no payment sessions exist for this batch
                has_payments = await self.batch_repo.has_payment_sessions(db, batch.id)
                if has_payments:
                    raise BatchCourseImmutableError(
                        "Cannot reassign course for a batch with existing payment sessions."
                    )

                if target_course.status == "ARCHIVED":
                    raise CourseArchivedError(
                        "Cannot reassign batch to an archived course."
                    )

                batch.course_id = target_course.id
                batch.course = target_course

        # 4. Handle status transition if requested
        if data.status is not None:
            target_status = data.status.upper().strip()
            if target_status not in ("ACTIVE", "INACTIVE", "ARCHIVED"):
                raise InvalidStateTransitionError("batch", batch.status, target_status)

            if batch.status == target_status:
                pass  # no-op
            elif batch.status in ("ACTIVE", "INACTIVE") and target_status in ("ACTIVE", "INACTIVE", "ARCHIVED"):
                batch.status = target_status
            else:
                raise InvalidStateTransitionError("batch", batch.status, target_status)

        # 5. Handle name update
        if data.name is not None:
            clean_name = data.name.strip()
            if not clean_name:
                raise ValueError("Batch name cannot be empty or whitespace only.")
            batch.name = clean_name

        # 6. Handle amount update
        if data.amount_inr is not None:
            if data.amount_inr <= 0:
                raise InvalidAmountError()
            batch.amount_inr = data.amount_inr

        # 7. Handle dates update and validation
        effective_starts = data.starts_at if data.starts_at is not None else batch.starts_at
        effective_ends = data.ends_at if data.ends_at is not None else batch.ends_at

        if effective_starts and effective_ends and effective_ends < effective_starts:
            raise InvalidDateRangeError()

        if data.starts_at is not None:
            batch.starts_at = data.starts_at
        if data.ends_at is not None:
            batch.ends_at = data.ends_at

        await self.batch_repo.update(db, batch)

        # Explicitly fetch course via async repository to prevent async lazy-load trigger
        course = await self.course_repo.get_by_id(db, batch.course_id)

        return BatchResponse(
            public_id=batch.public_id,
            course_public_id=course.public_id if course else uuid.UUID(int=0),
            course_name=course.name if course else None,
            name=batch.name,
            amount_inr=batch.amount_inr,
            status=batch.status,
            starts_at=batch.starts_at,
            ends_at=batch.ends_at,
            created_at=batch.created_at,
            updated_at=batch.updated_at,
        )

    async def get_batch_summary(
        self, db: AsyncSession, public_id: uuid.UUID
    ) -> "BatchSummaryResponse":
        """Compute aggregate summary metrics for a batch workspace via single-query database aggregations."""
        from sqlalchemy import case, func, select
        from app.models.payment_session import PaymentSession
        from app.models.reconciliation_run import ReconciliationRun
        from app.models.statement_import import StatementImport
        from app.schemas.batch import BatchSummaryResponse

        batch = await self.batch_repo.get_by_public_id_with_course(db, public_id)
        if not batch:
            raise BatchNotFoundError(str(public_id))

        # 1. Single aggregate query over PaymentSessions for this batch
        stmt = select(
            func.count(PaymentSession.id).label("payments_generated"),
            func.count(PaymentSession.id).filter(PaymentSession.status == "SUBMITTED").label("payments_submitted"),
            func.count(PaymentSession.id).filter(PaymentSession.status == "APPROVED").label("payments_approved"),
            func.coalesce(func.sum(PaymentSession.amount_inr), 0).label("expected_amount_inr"),
            func.coalesce(
                func.sum(case((PaymentSession.status == "APPROVED", PaymentSession.amount_inr), else_=0)),
                0,
            ).label("approved_amount_inr"),
        ).where(PaymentSession.batch_id == batch.id)

        res = await db.execute(stmt)
        row = res.one()

        # 2. Total statement import count
        stmt_count_res = await db.execute(select(func.count(StatementImport.id)))
        statement_count = stmt_count_res.scalar_one() or 0

        # 3. Latest reconciliation run for this batch
        latest_run_stmt = (
            select(ReconciliationRun)
            .where(ReconciliationRun.batch_id == batch.id)
            .order_by(ReconciliationRun.created_at.desc(), ReconciliationRun.id.desc())
            .limit(1)
        )
        latest_run_res = await db.execute(latest_run_stmt)
        latest_run = latest_run_res.scalar_one_or_none()

        return BatchSummaryResponse(
            batch_public_id=batch.public_id,
            batch_name=batch.name,
            course_name=batch.course.name if batch.course else "",
            amount_inr=batch.amount_inr,
            status=batch.status,
            payments_generated=row.payments_generated,
            payments_submitted=row.payments_submitted,
            payments_approved=row.payments_approved,
            expected_amount_inr=row.expected_amount_inr,
            approved_amount_inr=row.approved_amount_inr,
            statement_count=statement_count,
            latest_reconciliation_status=latest_run.status if latest_run else None,
            latest_reconciliation_run_public_id=latest_run.public_id if latest_run else None,
        )
