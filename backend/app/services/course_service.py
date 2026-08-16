"""Course service managing lifecycle, validations, and business logic."""

import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.course import Course
from app.repositories.course_repository import CourseRepository
from app.schemas.course import CourseCreate, CourseResponse, CourseUpdate
from app.services.exceptions import (
    CourseArchivedError,
    CourseNotFoundError,
    InvalidStateTransitionError,
)


class CourseService:
    """Business logic and lifecycle management for courses."""

    def __init__(self, course_repo: Optional[CourseRepository] = None):
        self.course_repo = course_repo or CourseRepository()

    async def create_course(
        self, db: AsyncSession, data: CourseCreate
    ) -> CourseResponse:
        """Create a new course with status ACTIVE or INACTIVE."""
        clean_name = data.name.strip()
        if not clean_name:
            raise ValueError("Course name cannot be empty or whitespace only.")

        clean_status = data.status.upper().strip()
        if clean_status not in ("ACTIVE", "INACTIVE"):
            raise InvalidStateTransitionError("course", "NONE", clean_status)

        course = Course(
            public_id=uuid.uuid4(),
            name=clean_name,
            description=data.description,
            status=clean_status,
        )
        await self.course_repo.create(db, course)
        return CourseResponse(
            public_id=course.public_id,
            name=course.name,
            description=course.description,
            status=course.status,
            batch_count=0,
            created_at=course.created_at,
            updated_at=course.updated_at,
        )

    async def get_course(
        self, db: AsyncSession, public_id: uuid.UUID
    ) -> CourseResponse:
        """Retrieve a course by public UUID with total batch count."""
        result = await self.course_repo.get_by_public_id_with_batch_count(db, public_id)
        if not result:
            raise CourseNotFoundError(str(public_id))
        course, batch_count = result
        return CourseResponse(
            public_id=course.public_id,
            name=course.name,
            description=course.description,
            status=course.status,
            batch_count=batch_count,
            created_at=course.created_at,
            updated_at=course.updated_at,
        )

    async def list_courses(
        self, db: AsyncSession, status: Optional[str] = None
    ) -> List[CourseResponse]:
        """List all courses with total batch count, optionally filtered by status."""
        filter_status = status.upper().strip() if status else None
        if filter_status and filter_status not in ("ACTIVE", "INACTIVE", "ARCHIVED"):
            raise ValueError("Status filter must be 'ACTIVE', 'INACTIVE', or 'ARCHIVED'.")

        rows = await self.course_repo.list_with_batch_counts(db, filter_status)
        return [
            CourseResponse(
                public_id=course.public_id,
                name=course.name,
                description=course.description,
                status=course.status,
                batch_count=batch_count,
                created_at=course.created_at,
                updated_at=course.updated_at,
            )
            for course, batch_count in rows
        ]

    async def update_course(
        self, db: AsyncSession, public_id: uuid.UUID, data: CourseUpdate
    ) -> CourseResponse:
        """Update a course enforcing the strict lifecycle state machine and immutability of ARCHIVED."""
        # 1. Lock course row
        course = await self.course_repo.get_by_public_id_for_update(db, public_id)
        if not course:
            raise CourseNotFoundError(str(public_id))

        # 2. Check if currently ARCHIVED -> ARCHIVED is terminal & strictly read-only
        if course.status == "ARCHIVED":
            raise CourseArchivedError("Course is archived and cannot be modified.")

        # 3. Handle status transition if requested
        if data.status is not None:
            target_status = data.status.upper().strip()
            if target_status not in ("ACTIVE", "INACTIVE", "ARCHIVED"):
                raise InvalidStateTransitionError("course", course.status, target_status)

            if course.status == target_status:
                pass  # no-op
            elif course.status in ("ACTIVE", "INACTIVE") and target_status in ("ACTIVE", "INACTIVE", "ARCHIVED"):
                course.status = target_status
            else:
                raise InvalidStateTransitionError("course", course.status, target_status)

        # 4. Handle name update
        if data.name is not None:
            clean_name = data.name.strip()
            if not clean_name:
                raise ValueError("Course name cannot be empty or whitespace only.")
            course.name = clean_name

        # 5. Handle description update
        if data.description is not None:
            course.description = data.description

        await self.course_repo.update(db, course)

        # Retrieve total batch count
        batch_count_res = await self.course_repo.get_by_public_id_with_batch_count(db, public_id)
        batch_count = batch_count_res[1] if batch_count_res else 0

        return CourseResponse(
            public_id=course.public_id,
            name=course.name,
            description=course.description,
            status=course.status,
            batch_count=batch_count,
            created_at=course.created_at,
            updated_at=course.updated_at,
        )
