"""Course repository for pure persistence operations."""

import uuid
from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
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

    async def list_all(
        self, session: AsyncSession, status: Optional[str] = None
    ) -> Sequence[Course]:
        """List all courses, optionally filtered by status."""
        stmt = select(Course).order_by(Course.created_at.desc())
        if status:
            stmt = stmt.where(Course.status == status)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def create(self, session: AsyncSession, course: Course) -> Course:
        """Persist a new course."""
        session.add(course)
        await session.flush()
        return course

    async def update(self, session: AsyncSession, course: Course) -> Course:
        """Update an existing course."""
        await session.flush()
        return course
