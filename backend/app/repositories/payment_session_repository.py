"""Payment session repository for pure persistence operations."""

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
