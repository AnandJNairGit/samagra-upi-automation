"""Payment submission repository for pure persistence operations."""

import uuid
from typing import Optional, Sequence
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.payment_submission import PaymentSubmission


class PaymentSubmissionRepository:
    """Persistence operations for payment submissions / UTR records."""

    async def get_by_id(
        self, session: AsyncSession, submission_id: int
    ) -> Optional[PaymentSubmission]:
        """Fetch payment submission by internal ID."""
        stmt = select(PaymentSubmission).where(PaymentSubmission.id == submission_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(
        self, session: AsyncSession, submission_id: int
    ) -> Optional[PaymentSubmission]:
        """Fetch payment submission with row-level lock (SELECT FOR UPDATE)."""
        stmt = (
            select(PaymentSubmission)
            .where(PaymentSubmission.id == submission_id)
            .with_for_update()
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_public_id(
        self, session: AsyncSession, public_id: uuid.UUID
    ) -> Optional[PaymentSubmission]:
        """Fetch payment submission by public UUID."""
        stmt = select(PaymentSubmission).where(PaymentSubmission.public_id == public_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_public_id_for_update(
        self, session: AsyncSession, public_id: uuid.UUID
    ) -> Optional[PaymentSubmission]:
        """Fetch payment submission by public UUID with row-level lock (SELECT FOR UPDATE)."""
        stmt = (
            select(PaymentSubmission)
            .where(PaymentSubmission.public_id == public_id)
            .with_for_update()
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_utr(
        self, session: AsyncSession, utr: str
    ) -> Optional[PaymentSubmission]:
        """Fetch payment submission by unique UTR."""
        stmt = select(PaymentSubmission).where(PaymentSubmission.utr == utr.strip())
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_current_for_session(
        self, session: AsyncSession, payment_session_id: int
    ) -> Optional[PaymentSubmission]:
        """Fetch the single current/active submission for a payment session."""
        stmt = select(PaymentSubmission).where(
            PaymentSubmission.payment_session_id == payment_session_id,
            PaymentSubmission.is_current.is_(True),
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_current_for_session_for_update(
        self, session: AsyncSession, payment_session_id: int
    ) -> Optional[PaymentSubmission]:
        """Fetch current submission with row-level lock (SELECT FOR UPDATE)."""
        stmt = (
            select(PaymentSubmission)
            .where(
                PaymentSubmission.payment_session_id == payment_session_id,
                PaymentSubmission.is_current.is_(True),
            )
            .with_for_update()
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_session_id(
        self, session: AsyncSession, payment_session_id: int
    ) -> Sequence[PaymentSubmission]:
        """List all submissions (historical and current) for a payment session."""
        stmt = (
            select(PaymentSubmission)
            .where(PaymentSubmission.payment_session_id == payment_session_id)
            .order_by(PaymentSubmission.submitted_at.desc())
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    async def deactivate_current_for_session(
        self, session: AsyncSession, payment_session_id: int
    ) -> int:
        """Mark any existing current submissions for the session as is_current=False."""
        stmt = (
            update(PaymentSubmission)
            .where(
                PaymentSubmission.payment_session_id == payment_session_id,
                PaymentSubmission.is_current.is_(True),
            )
            .values(is_current=False)
        )
        result = await session.execute(stmt)
        return result.rowcount

    async def create(
        self, session: AsyncSession, submission: PaymentSubmission
    ) -> PaymentSubmission:
        """Persist a new payment submission."""
        session.add(submission)
        await session.flush()
        return submission

    async def update(
        self, session: AsyncSession, submission: PaymentSubmission
    ) -> PaymentSubmission:
        """Update an existing payment submission."""
        await session.flush()
        return submission
