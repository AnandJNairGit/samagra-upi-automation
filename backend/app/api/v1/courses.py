"""Admin course management API router."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.dependencies import require_admin
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.course import CourseCreate, CourseResponse, CourseUpdate
from app.services.course_service import CourseService
from app.services.exceptions import (
    CourseArchivedError,
    CourseNotFoundError,
    InvalidStateTransitionError,
)

router = APIRouter()


def get_course_service() -> CourseService:
    """Dependency provider for CourseService."""
    return CourseService()


@router.get(
    "",
    response_model=List[CourseResponse],
    status_code=status.HTTP_200_OK,
    summary="List Courses",
)
async def list_courses(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (ACTIVE, INACTIVE, ARCHIVED)"),
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = require_admin,
    service: CourseService = Depends(get_course_service),
):
    """Retrieve all courses with total batch counts, optionally filtered by status."""
    try:
        return await service.list_courses(db, status=status_filter)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post(
    "",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Course",
)
async def create_course(
    payload: CourseCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = require_admin,
    service: CourseService = Depends(get_course_service),
):
    """Create a new course. Status defaults to ACTIVE; ARCHIVED status is rejected."""
    try:
        return await service.create_course(db, payload)
    except InvalidStateTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get(
    "/{course_public_id}",
    response_model=CourseResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Course",
)
async def get_course(
    course_public_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = require_admin,
    service: CourseService = Depends(get_course_service),
):
    """Retrieve a single course by public UUID."""
    try:
        return await service.get_course(db, course_public_id)
    except CourseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc


@router.patch(
    "/{course_public_id}",
    response_model=CourseResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Course",
)
async def update_course(
    course_public_id: uuid.UUID,
    payload: CourseUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = require_admin,
    service: CourseService = Depends(get_course_service),
):
    """Update course attributes and lifecycle status. ARCHIVED courses cannot be modified."""
    try:
        return await service.update_course(db, course_public_id, payload)
    except CourseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
    except CourseArchivedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    except InvalidStateTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
