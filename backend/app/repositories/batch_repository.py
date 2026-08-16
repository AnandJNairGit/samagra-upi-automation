"""Batch repository for pure persistence operations."""

import uuid
from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.batch import Batch
from app.models.payment_session import PaymentSession


class BatchRepository:
    """Persistence operations for cohorts/batches."""

    async def get_by_id(self, session: AsyncSession, batch_id: int) -> Optional[Batch]:
        """Fetch batch by internal ID."""
        stmt = select(Batch).where(Batch.id == batch_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_public_id(
        self, session: AsyncSession, public_id: uuid.UUID
    ) -> Optional[Batch]:
        """Fetch batch by public UUID."""
        stmt = select(Batch).where(Batch.public_id == public_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_public_id_with_course(
        self, session: AsyncSession, public_id: uuid.UUID
    ) -> Optional[Batch]:
        """Fetch batch by public UUID with course eager-loaded."""
        stmt = (
            select(Batch)
            .options(joinedload(Batch.course))
            .where(Batch.public_id == public_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_public_id_for_update(
        self, session: AsyncSession, public_id: uuid.UUID
    ) -> Optional[Batch]:
        """Fetch batch by public UUID with row lock."""
        stmt = (
            select(Batch)
            .where(Batch.public_id == public_id)
            .with_for_update()
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_course_id(
        self, session: AsyncSession, course_id: int, status: Optional[str] = None
    ) -> Sequence[Batch]:
        """List all batches under a specific course, optionally filtered by status."""
        stmt = (
            select(Batch)
            .where(Batch.course_id == course_id)
            .order_by(Batch.starts_at.desc().nullslast(), Batch.created_at.desc(), Batch.id.desc())
        )
        if status:
            stmt = stmt.where(Batch.status == status)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def list_all_with_course(
        self,
        session: AsyncSession,
        course_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> Sequence[Batch]:
        """List batches with course eager loaded, optionally filtered by course_id and/or status."""
        stmt = (
            select(Batch)
            .options(joinedload(Batch.course))
            .order_by(Batch.starts_at.desc().nullslast(), Batch.created_at.desc(), Batch.id.desc())
        )
        if course_id is not None:
            stmt = stmt.where(Batch.course_id == course_id)
        if status:
            stmt = stmt.where(Batch.status == status)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def has_payment_sessions(self, session: AsyncSession, batch_id: int) -> bool:
        """Check if any payment sessions exist for this batch via SQL EXISTS."""
        stmt = select(
            select(PaymentSession.id)
            .where(PaymentSession.batch_id == batch_id)
            .exists()
        )
        result = await session.execute(stmt)
        return bool(result.scalar())

    async def create(self, session: AsyncSession, batch: Batch) -> Batch:
        """Persist a new batch."""
        session.add(batch)
        await session.flush()
        await session.refresh(batch)
        return batch

    async def update(self, session: AsyncSession, batch: Batch) -> Batch:
        """Update an existing batch."""
        await session.flush()
        await session.refresh(batch)
        return batch


