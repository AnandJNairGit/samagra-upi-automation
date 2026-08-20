"""Protected admin endpoints for health, dashboard summary metrics, and payment inspection."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.dependencies import require_admin
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.admin_payment import (
    AdminDashboardSummaryResponse,
    AdminPaymentDetailResponse,
    AdminPaymentListResponse,
)
from app.schemas.auth import AdminHealthResponse
from app.services.admin_payment_service import AdminPaymentService
from app.services.payment_submission_service import PaymentSubmissionService
from app.services.exceptions import InvalidSessionStateError, PaymentSessionUnavailableError

router = APIRouter()


def get_admin_payment_service() -> AdminPaymentService:
    """Dependency injector for AdminPaymentService."""
    return AdminPaymentService()


def get_payment_submission_service() -> PaymentSubmissionService:
    """Dependency injector for PaymentSubmissionService."""
    return PaymentSubmissionService()


@router.get(
    "/health",
    response_model=AdminHealthResponse,
    summary="Protected Admin Health Verification",
)
async def admin_health(
    current_admin: AdminUser = require_admin,
):
    """Protected health endpoint to verify admin authorization middleware."""
    return AdminHealthResponse(
        status="ok",
        authenticated=True,
        admin_email=current_admin.email,
        admin_public_id=current_admin.public_id,
    )


@router.get(
    "/dashboard/summary",
    response_model=AdminDashboardSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch Admin Dashboard Payment Summary Metrics",
)
async def get_admin_dashboard_summary(
    current_admin: AdminUser = require_admin,
    db: AsyncSession = Depends(get_db),
    service: AdminPaymentService = Depends(get_admin_payment_service),
):
    """Read-only dashboard summary endpoint providing aggregate metrics.

    Calculated via single-query database aggregation over existing PaymentSession and
    PaymentSubmission records. Revenue total strictly counts APPROVED sessions.
    """
    try:
        return await service.get_dashboard_summary(db)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to calculate payment summary metrics.",
        ) from exc


@router.get(
    "/payments",
    response_model=AdminPaymentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Admin Payment Sessions with Filtering and Search",
)
async def list_admin_payments(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by payment session status"),
    course_public_id: Optional[uuid.UUID] = Query(None, alias="course_public_id", description="Filter by course public UUID"),
    batch_public_id: Optional[uuid.UUID] = Query(None, alias="batch_public_id", description="Filter by batch public UUID"),
    search: Optional[str] = Query(None, alias="search", description="Text search across participant name, phone, email, reference ID, and current UTR"),
    reference_id: Optional[str] = Query(None, alias="reference_id", description="Exact match on payment reference ID"),
    utr: Optional[str] = Query(None, alias="utr", description="Exact match on current UTR"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    current_admin: AdminUser = require_admin,
    db: AsyncSession = Depends(get_db),
    service: AdminPaymentService = Depends(get_admin_payment_service),
):
    """Paginated, filtered, and searchable list of payment sessions for authenticated administrators.

    Read-Only & History Preserving:
        - Displays historical course name, batch name, and amount snapshots.
        - Outer joins current PaymentSubmission (is_current = True) to prevent duplicate rows.
        - Deterministic ordering: created_at DESC, id DESC.
    """
    try:
        return await service.list_payments(
            db=db,
            status=status_filter,
            course_public_id=course_public_id,
            batch_public_id=batch_public_id,
            search=search,
            reference_id=reference_id,
            utr=utr,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch payment list.",
        ) from exc


@router.get(
    "/payments/submitted",
    response_model=AdminPaymentListResponse,
    status_code=status.HTTP_200_OK,
    summary="Convenience Endpoint for Submitted Payments",
)
async def list_submitted_admin_payments(
    course_public_id: Optional[uuid.UUID] = Query(None, alias="course_public_id"),
    batch_public_id: Optional[uuid.UUID] = Query(None, alias="batch_public_id"),
    search: Optional[str] = Query(None, alias="search"),
    reference_id: Optional[str] = Query(None, alias="reference_id"),
    utr: Optional[str] = Query(None, alias="utr"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_admin: AdminUser = require_admin,
    db: AsyncSession = Depends(get_db),
    service: AdminPaymentService = Depends(get_admin_payment_service),
):
    """Convenience read-only shortcut for listing payments in SUBMITTED status.

    IMPORTANT ROUTE ORDERING:
        Registered before /payments/{payment_session_public_id} to avoid matching 'submitted' as a UUID parameter.
        Reuses identical service logic as /payments?status=SUBMITTED.
    """
    try:
        return await service.list_payments(
            db=db,
            status="SUBMITTED",
            course_public_id=course_public_id,
            batch_public_id=batch_public_id,
            search=search,
            reference_id=reference_id,
            utr=utr,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch submitted payment list.",
        ) from exc


@router.get(
    "/payments/{payment_session_public_id}",
    response_model=AdminPaymentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch Detailed Payment Record for Admin Inspection",
)
async def get_admin_payment_detail(
    payment_session_public_id: uuid.UUID,
    current_admin: AdminUser = require_admin,
    db: AsyncSession = Depends(get_db),
    service: AdminPaymentService = Depends(get_admin_payment_service),
):
    """Detailed read-only payment inspection record.

    Includes participant info, historical training/financial snapshots, current submission,
    and historical submission attempts.
    """
    try:
        return await service.get_payment_detail(db, payment_session_public_id)
    except PaymentSessionUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load payment details.",
        ) from exc


@router.post(
    "/payments/{payment_session_public_id}/approve",
    response_model=AdminPaymentDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve Payment Session",
)
async def approve_admin_payment(
    payment_session_public_id: uuid.UUID,
    current_admin: AdminUser = require_admin,
    db: AsyncSession = Depends(get_db),
    admin_payment_service: AdminPaymentService = Depends(get_admin_payment_service),
    submission_service: PaymentSubmissionService = Depends(get_payment_submission_service),
):
    """Admin approval of a payment session and its submission."""
    try:
        await submission_service.approve_payment_session_by_public_id(
            db=db,
            payment_session_public_id=payment_session_public_id,
            admin_id=current_admin.id,
        )
        await db.commit()
        return await admin_payment_service.get_payment_detail(db, payment_session_public_id)
    except PaymentSessionUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
    except InvalidSessionStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=exc.message,
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to approve payment session.",
        ) from exc
