"""Batch repository for pure persistence operations."""

import uuid
from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.batch import Batch


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

    async def list_by_course_id(
        self, session: AsyncSession, course_id: int, status: Optional[str] = None
    ) -> Sequence[Batch]:
        """List all batches under a specific course, optionally filtered by status."""
        stmt = (
            select(Batch)
            .where(Batch.course_id == course_id)
            .order_by(Batch.created_at.desc())
        )
        if status:
            stmt = stmt.where(Batch.status == status)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def create(self, session: AsyncSession, batch: Batch) -> Batch:
        """Persist a new batch."""
        session.add(batch)
        await session.flush()
        return batch

    async def update(self, session: AsyncSession, batch: Batch) -> Batch:
        """Update an existing batch."""
        await session.flush()
        return batch
