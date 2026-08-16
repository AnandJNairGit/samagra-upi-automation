"""Public unauthenticated registration and UPI payment API router."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.dependencies import get_client_ip
from app.auth.rate_limiter import auth_rate_limiter
from app.core.database import get_db
from app.schemas.payment_session import (
    PaymentSessionCreateRequest,
    PaymentSessionPublicResponse,
)
from app.schemas.public import (
    PublicBatchResponse,
    PublicRegistrationValidateRequest,
    PublicRegistrationValidateResponse,
)
from app.services.exceptions import (
    ParticipantValidationError,
    PaymentSessionUnavailableError,
    PublicBatchUnavailableError,
)
from app.services.payment_session_service import PaymentSessionService
from app.services.public_registration_service import PublicRegistrationService

router = APIRouter()


def get_public_registration_service() -> PublicRegistrationService:
    """Dependency injector for PublicRegistrationService."""
    return PublicRegistrationService()


def get_payment_session_service() -> PaymentSessionService:
    """Dependency injector for PaymentSessionService."""
    return PaymentSessionService()


@router.get(
    "/batches/{batch_public_id}",
    response_model=PublicBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolve Public Cohort Registration Link",
)
async def get_public_batch(
    batch_public_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    service: PublicRegistrationService = Depends(get_public_registration_service),
):
    """Public read-only lookup to resolve course, batch, and fee details for a shared registration link.

    Availability Rule:
        Requires both batch.status == 'ACTIVE' AND course.status == 'ACTIVE'.
        Unavailable, inactive, or archived entities return generic 404.
    """
    client_ip = get_client_ip(request) or "unknown"

    # Rate limiting: Max 60 batch lookups per 60 seconds per IP
    rate_key = f"public:batch:{client_ip}"
    allowed, retry_after = auth_rate_limiter.check(rate_key, max_requests=60, window_seconds=60)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    try:
        return await service.get_active_batch_by_public_id(db, batch_public_id)
    except PublicBatchUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc


@router.post(
    "/register/validate",
    response_model=PublicRegistrationValidateResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate Participant Registration Context",
)
async def validate_public_registration(
    payload: PublicRegistrationValidateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    service: PublicRegistrationService = Depends(get_public_registration_service),
):
    """Validate participant registration details against active cohort without creating payment sessions.

    Phase 5 / Phase 6 Boundary:
        Authoritative course, batch name, and amount are derived from the database.
        Returns validated registration context for Phase 6 payment handoff.
    """
    client_ip = get_client_ip(request) or "unknown"

    # Rate limiting: Max 20 validation attempts per 60 seconds per IP + batch_id
    rate_key = f"validate:{client_ip}:{payload.batch_public_id}"
    allowed, retry_after = auth_rate_limiter.check(rate_key, max_requests=20, window_seconds=60)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many validation attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    try:
        return await service.validate_registration_context(db, payload)
    except PublicBatchUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
    except ParticipantValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.message,
        ) from exc


@router.post(
    "/payment-sessions",
    response_model=PaymentSessionPublicResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Public Payment Session & Generate UPI QR Context",
)
async def create_public_payment_session(
    payload: PaymentSessionCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    service: PaymentSessionService = Depends(get_payment_session_service),
):
    """Create a new PaymentSession for an active cohort and generate authoritative UPI QR data.

    Phase 6 Boundary:
        - Server derives authoritative amount from batch.
        - Server generates unique reference ID.
        - Server generates standard UPI Intent URI.
        - Status is initialized to PENDING.
        - Zero PaymentSubmission records created.
    """
    client_ip = get_client_ip(request) or "unknown"

    # Rate limiting: Max 20 payment session creation attempts per 60 seconds per IP + batch_id
    rate_key = f"pay_create:{client_ip}:{payload.batch_public_id}"
    allowed, retry_after = auth_rate_limiter.check(rate_key, max_requests=20, window_seconds=60)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many payment creation attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    try:
        return await service.create_payment_session(db, payload)
    except PublicBatchUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create payment session. Please try again.",
        ) from exc


@router.get(
    "/payment-sessions/{payment_session_public_id}",
    response_model=PaymentSessionPublicResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch Public Payment Session for Payment Page",
)
async def get_public_payment_session(
    payment_session_public_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    service: PaymentSessionService = Depends(get_payment_session_service),
):
    """Fetch public checkout data to render the UPI payment page and QR code.

    Read-Only & Safe Public Exposure:
        - Omits database internal IDs and admin metadata.
        - If session is not found, returns 404.
    """
    client_ip = get_client_ip(request) or "unknown"

    # Rate limiting: Max 60 payment session lookups per 60 seconds per IP
    rate_key = f"pay_lookup:{client_ip}"
    allowed, retry_after = auth_rate_limiter.check(rate_key, max_requests=60, window_seconds=60)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    try:
        return await service.get_public_payment_session(db, payment_session_public_id)
    except PaymentSessionUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
