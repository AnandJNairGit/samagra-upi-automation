"""Course repository for pure persistence operations."""

import uuid
from typing import Optional, Sequence, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.batch import Batch
from app.models.course import Course


class CourseRepository:
    """Persistence operations for courses."""

    async def get_by_id(self, session: AsyncSession, course_id: int) -> Optional[Course]:
        """Fetch course by internal ID."""
        stmt = select(Course).where(Course.id == course_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_public_id(
        self, session: AsyncSession, public_id: uuid.UUID
    ) -> Optional[Course]:
        """Fetch course by public UUID."""
        stmt = select(Course).where(Course.public_id == public_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_public_id_for_update(
        self, session: AsyncSession, public_id: uuid.UUID
    ) -> Optional[Course]:
        """Fetch course by public UUID with row-level lock (SELECT FOR UPDATE)."""
        stmt = (
            select(Course)
            .where(Course.public_id == public_id)
            .with_for_update()
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(
        self, session: AsyncSession, course_id: int
    ) -> Optional[Course]:
        """Fetch course by internal ID with row-level lock (SELECT FOR UPDATE)."""
        stmt = (
            select(Course)
            .where(Course.id == course_id)
            .with_for_update()
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self, session: AsyncSession, status: Optional[str] = None
    ) -> Sequence[Course]:
        """List all courses, optionally filtered by status, with deterministic ordering."""
        stmt = select(Course).order_by(Course.created_at.desc(), Course.id.desc())
        if status:
            stmt = stmt.where(Course.status == status)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def list_with_batch_counts(
        self, session: AsyncSession, status: Optional[str] = None
    ) -> Sequence[Tuple[Course, int]]:
        """List courses with total batch count using a single outer-join grouped query."""
        stmt = (
            select(Course, func.count(Batch.id).label("batch_count"))
            .outerjoin(Batch, Batch.course_id == Course.id)
            .group_by(Course.id)
            .order_by(Course.created_at.desc(), Course.id.desc())
        )
        if status:
            stmt = stmt.where(Course.status == status)
        result = await session.execute(stmt)
        return result.all()

    async def get_by_public_id_with_batch_count(
        self, session: AsyncSession, public_id: uuid.UUID
    ) -> Optional[Tuple[Course, int]]:
        """Fetch single course with total batch count."""
        stmt = (
            select(Course, func.count(Batch.id).label("batch_count"))
            .outerjoin(Batch, Batch.course_id == Course.id)
            .where(Course.public_id == public_id)
            .group_by(Course.id)
        )
        result = await session.execute(stmt)
        row = result.first()
        if row:
            return row[0], row[1]
        return None

    async def create(self, session: AsyncSession, course: Course) -> Course:
        """Persist a new course."""
        session.add(course)
        await session.flush()
        await session.refresh(course)
        return course

    async def update(self, session: AsyncSession, course: Course) -> Course:
        """Update an existing course."""
        await session.flush()
        await session.refresh(course)
        return course


