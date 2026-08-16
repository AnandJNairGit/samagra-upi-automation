"""Admin batch management API router."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.dependencies import require_admin
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.batch import BatchCreate, BatchResponse, BatchUpdate
from app.services.batch_service import BatchService
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

router = APIRouter()


def get_batch_service() -> BatchService:
    """Dependency provider for BatchService."""
    return BatchService()


@router.get(
    "",
    response_model=List[BatchResponse],
    status_code=status.HTTP_200_OK,
    summary="List Batches",
)
async def list_batches(
    course_public_id: Optional[uuid.UUID] = Query(None, description="Filter by Course public UUID"),
    course_id: Optional[uuid.UUID] = Query(None, description="Alias for course_public_id"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (ACTIVE, INACTIVE, ARCHIVED)"),
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = require_admin,
    service: BatchService = Depends(get_batch_service),
):
    """Retrieve all batches with course metadata, optionally filtered by course UUID and/or status."""
    effective_course_uuid = course_public_id or course_id
    try:
        return await service.list_batches(
            db, course_public_id=effective_course_uuid, status=status_filter
        )
    except CourseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post(
    "",
    response_model=BatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Batch",
)
async def create_batch(
    payload: BatchCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = require_admin,
    service: BatchService = Depends(get_batch_service),
):
    """Create a new batch under an existing course. Status defaults to ACTIVE; ARCHIVED is forbidden."""
    try:
        return await service.create_batch(db, payload)
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
    except (InvalidAmountError, InvalidDateRangeError, ValueError) as exc:
        msg = exc.message if hasattr(exc, "message") else str(exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=msg,
        ) from exc


@router.get(
    "/{batch_public_id}",
    response_model=BatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Batch",
)
async def get_batch(
    batch_public_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = require_admin,
    service: BatchService = Depends(get_batch_service),
):
    """Retrieve a single batch by public UUID with course details."""
    try:
        return await service.get_batch(db, batch_public_id)
    except BatchNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc


@router.patch(
    "/{batch_public_id}",
    response_model=BatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Batch",
)
async def update_batch(
    batch_public_id: uuid.UUID,
    payload: BatchUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: AdminUser = require_admin,
    service: BatchService = Depends(get_batch_service),
):
    """Update batch attributes, amount, dates, or status. Reassigning course is forbidden if payment sessions exist."""
    try:
        return await service.update_batch(db, batch_public_id, payload)
    except BatchNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
    except CourseNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
    except (BatchArchivedError, CourseArchivedError, BatchCourseImmutableError, InvalidStateTransitionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc
    except (InvalidAmountError, InvalidDateRangeError, ValueError) as exc:
        msg = exc.message if hasattr(exc, "message") else str(exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=msg,
        ) from exc
