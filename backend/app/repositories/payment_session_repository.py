"""Payment session repository for pure persistence operations."""

from __future__ import annotations

import uuid
from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.payment_session import PaymentSession


class PaymentSessionRepository:
    """Persistence operations for payment sessions."""

    async def get_by_id(
        self, session: AsyncSession, session_id: int
    ) -> Optional[PaymentSession]:
        """Fetch payment session by internal ID."""
        stmt = select(PaymentSession).where(PaymentSession.id == session_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(
        self, session: AsyncSession, session_id: int
    ) -> Optional[PaymentSession]:
        """Fetch payment session with row-level lock (SELECT FOR UPDATE)."""
        stmt = (
            select(PaymentSession)
            .where(PaymentSession.id == session_id)
            .with_for_update()
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_public_id(
        self, session: AsyncSession, public_id: uuid.UUID
    ) -> Optional[PaymentSession]:
        """Fetch payment session by public UUID."""
        stmt = select(PaymentSession).where(PaymentSession.public_id == public_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_public_id_for_update(
        self, session: AsyncSession, public_id: uuid.UUID
    ) -> Optional[PaymentSession]:
        """Fetch payment session by public UUID with row-level lock (SELECT FOR UPDATE)."""
        stmt = (
            select(PaymentSession)
            .where(PaymentSession.public_id == public_id)
            .with_for_update()
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_reference_id(
        self, session: AsyncSession, reference_id: str
    ) -> Optional[PaymentSession]:
        """Fetch payment session by unique reference ID."""
        stmt = select(PaymentSession).where(PaymentSession.reference_id == reference_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_reference_ids_bulk(
        self, session: AsyncSession, reference_ids: Sequence[str]
    ) -> dict[str, tuple[PaymentSession, Optional[PaymentSubmission]]]:
        """Fetch dictionary mapping reference_id -> (PaymentSession, active PaymentSubmission) for bulk reconciliation."""
        if not reference_ids:
            return {}

        from app.models.payment_submission import PaymentSubmission

        clean_ids = list({r.strip() for r in reference_ids if r and r.strip()})
        if not clean_ids:
            return {}

        result_map: dict[str, tuple[PaymentSession, Optional[PaymentSubmission]]] = {}
        chunk_size = 500

        for i in range(0, len(clean_ids), chunk_size):
            chunk = clean_ids[i : i + chunk_size]
            stmt = (
                select(PaymentSession, PaymentSubmission)
                .outerjoin(
                    PaymentSubmission,
                    (PaymentSubmission.payment_session_id == PaymentSession.id)
                    & (PaymentSubmission.is_current.is_(True)),
                )
                .where(PaymentSession.reference_id.in_(chunk))
            )
            res = await session.execute(stmt)
            for ps, submission in res.all():
                result_map[ps.reference_id] = (ps, submission)

        return result_map


    async def list_all(
        self,
        session: AsyncSession,
        batch_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> Sequence[PaymentSession]:
        """List payment sessions with optional filtering."""
        stmt = select(PaymentSession).order_by(PaymentSession.created_at.desc())
        if batch_id is not None:
            stmt = stmt.where(PaymentSession.batch_id == batch_id)
        if status:
            stmt = stmt.where(PaymentSession.status == status)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def get_dashboard_summary(self, session: AsyncSession) -> dict:
        """Calculate read-only payment summary metrics using database aggregation."""
        from sqlalchemy import case, func

        stmt = select(
            func.count(PaymentSession.id).label("total_registrations"),
            func.count(PaymentSession.id).filter(PaymentSession.status == "PENDING").label("pending_payments"),
            func.count(PaymentSession.id).filter(PaymentSession.status == "SUBMITTED").label("submitted_payments"),
            func.count(PaymentSession.id).filter(PaymentSession.status == "APPROVED").label("approved_payments"),
            func.count(PaymentSession.id).filter(PaymentSession.status == "REJECTED").label("rejected_payments"),
            func.coalesce(
                func.sum(
                    case((PaymentSession.status == "APPROVED", PaymentSession.amount_inr), else_=0)
                ),
                0,
            ).label("total_amount_collected_inr"),
        )
        result = await session.execute(stmt)
        row = result.one()
        return {
            "total_registrations": row.total_registrations,
            "pending_payments": row.pending_payments,
            "submitted_payments": row.submitted_payments,
            "approved_payments": row.approved_payments,
            "rejected_payments": row.rejected_payments,
            "total_amount_collected_inr": row.total_amount_collected_inr,
        }

    async def list_admin_payments(
        self,
        session: AsyncSession,
        status: Optional[str] = None,
        course_id: Optional[int] = None,
        batch_id: Optional[int] = None,
        search: Optional[str] = None,
        reference_id: Optional[str] = None,
        utr: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[tuple[PaymentSession, Course, Batch, Optional[PaymentSubmission]]], int]:
        """List payment sessions for admin console with filtering, search, outer-joined current submission, and pagination."""
        from sqlalchemy import func, or_
        from app.models.batch import Batch
        from app.models.course import Course
        from app.models.payment_submission import PaymentSubmission

        # Base query joining Course, Batch, and current PaymentSubmission (LEFT JOIN where is_current = True)
        base_stmt = (
            select(PaymentSession, Course, Batch, PaymentSubmission)
            .join(Course, PaymentSession.course_id == Course.id)
            .join(Batch, PaymentSession.batch_id == Batch.id)
            .outerjoin(
                PaymentSubmission,
                (PaymentSubmission.payment_session_id == PaymentSession.id)
                & (PaymentSubmission.is_current.is_(True)),
            )
        )

        # Build composable filters
        conditions = []
        if status:
            conditions.append(PaymentSession.status == status)
        if course_id is not None:
            conditions.append(PaymentSession.course_id == course_id)
        if batch_id is not None:
            conditions.append(PaymentSession.batch_id == batch_id)
        if reference_id:
            conditions.append(PaymentSession.reference_id == reference_id.strip())
        if utr:
            conditions.append(PaymentSubmission.utr == utr.strip())
        if search and search.strip():
            clean_search = f"%{search.strip()}%"
            conditions.append(
                or_(
                    PaymentSession.full_name.ilike(clean_search),
                    PaymentSession.phone.ilike(clean_search),
                    PaymentSession.email.ilike(clean_search),
                    PaymentSession.reference_id.ilike(clean_search),
                    PaymentSubmission.utr.ilike(clean_search),
                )
            )

        if conditions:
            base_stmt = base_stmt.where(*conditions)

        # Total matching count query (select count(*) from subquery)
        subq = base_stmt.subquery()
        count_stmt = select(func.count()).select_from(subq)
        total_result = await session.execute(count_stmt)
        total = total_result.scalar_one()

        # Deterministic sorting & pagination
        offset = (page - 1) * page_size
        paginated_stmt = (
            base_stmt.order_by(PaymentSession.created_at.desc(), PaymentSession.id.desc())
            .offset(offset)
            .limit(page_size)
        )

        result = await session.execute(paginated_stmt)
        items = result.all()  # List of (PaymentSession, Course, Batch, PaymentSubmission) tuples
        return items, total

    async def get_admin_payment_detail_by_public_id(
        self, session: AsyncSession, public_id: uuid.UUID
    ) -> Optional[tuple[PaymentSession, Course, Batch]]:
        """Fetch payment session with associated Course and Batch for admin inspection."""
        from app.models.batch import Batch
        from app.models.course import Course

        stmt = (
            select(PaymentSession, Course, Batch)
            .join(Course, PaymentSession.course_id == Course.id)
            .join(Batch, PaymentSession.batch_id == Batch.id)
            .where(PaymentSession.public_id == public_id)
        )
        result = await session.execute(stmt)
        return result.first()

    async def create(
        self, session: AsyncSession, payment_session: PaymentSession
    ) -> PaymentSession:
        """Persist a new payment session."""
        session.add(payment_session)
        await session.flush()
        return payment_session

    async def update(
        self, session: AsyncSession, payment_session: PaymentSession
    ) -> PaymentSession:
        """Update an existing payment session."""
        await session.flush()
        return payment_session
