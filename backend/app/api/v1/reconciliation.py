"""Admin reconciliation API endpoints."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.reconciliation import (
    ReconciliationResultDetailResponse,
    ReconciliationResultListResponse,
    ReconciliationRunCreateRequest,
    ReconciliationRunListResponse,
    ReconciliationRunResponse,
)
from app.services.exceptions import (
    DomainError,
    ReconciliationResultNotFoundError,
    ReconciliationRunNotFoundError,
    StatementImportNotReadyError,
)
from app.services.reconciliation_service import ReconciliationService

router = APIRouter()


@router.post(
    "/runs",
    response_model=ReconciliationRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start payment reconciliation run",
    description="Initiates an administrative payment reconciliation run for a specific batch against an imported bank statement file.",
)
async def start_reconciliation_run(
    payload: ReconciliationRunCreateRequest,
    current_admin: AdminUser = require_admin,
    db: AsyncSession = Depends(get_db),
):
    """Start a new payment reconciliation execution pass."""
    service = ReconciliationService()
    try:
        return await service.run_reconciliation(
            db=db,
            batch_public_id=payload.batch_public_id,
            statement_import_public_id=payload.statement_import_public_id,
            admin_user=current_admin,
        )
    except StatementImportNotReadyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except DomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.get(
    "/runs",
    response_model=ReconciliationRunListResponse,
    summary="List reconciliation runs",
    description="Fetch paginated list of past reconciliation runs with summary statistics.",
)
async def list_reconciliation_runs(
    statement_import_public_id: Optional[uuid.UUID] = Query(None, description="Filter runs by statement import UUID"),
    batch_public_id: Optional[uuid.UUID] = Query(None, description="Filter runs by batch UUID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_admin: AdminUser = require_admin,
    db: AsyncSession = Depends(get_db),
):
    """List paginated reconciliation runs."""
    service = ReconciliationService()
    return await service.list_runs_paginated(
        db=db,
        statement_import_public_id=statement_import_public_id,
        batch_public_id=batch_public_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/runs/{run_public_id}",
    response_model=ReconciliationRunResponse,
    summary="Fetch single reconciliation run",
    description="Fetch details and summary metric counts for a single reconciliation run by public UUID.",
)
async def get_reconciliation_run(
    run_public_id: uuid.UUID,
    current_admin: AdminUser = require_admin,
    db: AsyncSession = Depends(get_db),
):
    """Fetch single reconciliation run metadata."""
    service = ReconciliationService()
    try:
        return await service.get_run_by_public_id(db=db, public_id=run_public_id)
    except ReconciliationRunNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get(
    "/runs/{run_public_id}/results",
    response_model=ReconciliationResultListResponse,
    summary="List reconciliation run results",
    description="Fetch paginated transaction classification results for a reconciliation run.",
)
async def list_reconciliation_results_for_run(
    run_public_id: uuid.UUID,
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by classification status (e.g. MATCHED, AMOUNT_MISMATCH, UTR_MISMATCH, UNKNOWN_REFERENCE, NO_REFERENCE, DUPLICATE_TRANSACTION, UNMATCHED)"),
    reason_code: Optional[str] = Query(None, description="Filter by machine reason code"),
    search: Optional[str] = Query(None, description="Search by reference ID, UTR, or participant name"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_admin: AdminUser = require_admin,
    db: AsyncSession = Depends(get_db),
):
    """List paginated results for a reconciliation run."""
    service = ReconciliationService()
    try:
        return await service.list_results_for_run_paginated(
            db=db,
            run_public_id=run_public_id,
            status=status_filter,
            reason_code=reason_code,
            search=search,
            page=page,
            page_size=page_size,
        )
    except ReconciliationRunNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get(
    "/results/{result_public_id}",
    response_model=ReconciliationResultDetailResponse,
    summary="Fetch single reconciliation result detail",
    description="Fetch full explainability inspection record for a single reconciliation result.",
)
async def get_reconciliation_result_detail(
    result_public_id: uuid.UUID,
    current_admin: AdminUser = require_admin,
    db: AsyncSession = Depends(get_db),
):
    """Fetch full inspection detail for a single reconciliation result."""
    service = ReconciliationService()
    try:
        return await service.get_result_detail_by_public_id(db=db, public_id=result_public_id)
    except ReconciliationResultNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get(
    "/results/by-session/{payment_session_public_id}",
    response_model=ReconciliationResultDetailResponse,
    summary="Fetch latest reconciliation result by payment session",
    description="Fetch full explainability inspection record for the most recent reconciliation result of a payment session.",
)
async def get_latest_reconciliation_result_by_session(
    payment_session_public_id: uuid.UUID,
    current_admin: AdminUser = require_admin,
    db: AsyncSession = Depends(get_db),
):
    """Fetch full inspection detail for the most recent reconciliation result of a payment session."""
    service = ReconciliationService()
    try:
        return await service.get_latest_result_by_payment_session_public_id(db=db, payment_session_public_id=payment_session_public_id)
    except ReconciliationResultNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
