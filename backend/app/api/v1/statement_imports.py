"""Protected admin endpoints for statement import previews, confirmations, history, and transaction inspection."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin
from app.core.database import get_db
from app.models.admin_user import AdminUser
from app.schemas.statement_import import (
    BankTransactionListResponse,
    ImportConfirmRequest,
    ImportPreviewResponse,
    ImportSummaryResponse,
    StatementImportDetailResponse,
    StatementImportListResponse,
)
from app.services.statement_import_service import StatementImportService

from app.core.logging import logger

router = APIRouter()


def get_statement_import_service() -> StatementImportService:
    """Dependency injector for StatementImportService."""
    return StatementImportService()


@router.post(
    "/preview",
    response_model=ImportPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload & Preview Statement File (0 DB Writes)",
)
async def preview_statement_import(
    file: UploadFile = File(...),
    sheet_name: Optional[str] = Form(None),
    header_row_index: int = Form(1),
    current_admin: AdminUser = require_admin,
    service: StatementImportService = Depends(get_statement_import_service),
):
    """Step 1: Inspect uploaded statement file (.csv / .xlsx), detect sheets/headers, and generate preview token."""
    try:
        file_bytes = await file.read()
        return service.preview_import(
            file_bytes=file_bytes,
            filename=file.filename or "statement.csv",
            admin_user_id=current_admin.id,
            sheet_name=sheet_name,
            header_row_index=header_row_index,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to process statement preview.",
        ) from exc


@router.post(
    "/confirm",
    response_model=ImportSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm Statement Import with Mapped Columns",
)
async def confirm_statement_import(
    payload: ImportConfirmRequest,
    current_admin: AdminUser = require_admin,
    db: AsyncSession = Depends(get_db),
    service: StatementImportService = Depends(get_statement_import_service),
):
    """Step 2: Confirm import with column mappings, validate rows, deduplicate txns, and persist BankTransactions."""
    try:
        return await service.confirm_import(
            db=db,
            admin_user_id=current_admin.id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unable to confirm statement import", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to confirm statement import: {str(exc)}",
        ) from exc


@router.get(
    "",
    response_model=StatementImportListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Statement Import History for Admin",
)
async def list_statement_imports(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    current_admin: AdminUser = require_admin,
    db: AsyncSession = Depends(get_db),
    service: StatementImportService = Depends(get_statement_import_service),
):
    """Fetch paginated audit history of past statement imports."""
    try:
        return await service.list_imports(db=db, page=page, page_size=page_size)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch statement import history.",
        ) from exc


@router.get(
    "/{import_public_id}",
    response_model=StatementImportDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch Statement Import Detail Record",
)
async def get_statement_import_detail(
    import_public_id: uuid.UUID,
    current_admin: AdminUser = require_admin,
    db: AsyncSession = Depends(get_db),
    service: StatementImportService = Depends(get_statement_import_service),
):
    """Fetch detailed audit record for a completed statement import."""
    try:
        return await service.get_import_detail(db=db, import_public_id=import_public_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch statement import detail.",
        ) from exc


@router.get(
    "/{import_public_id}/transactions",
    response_model=BankTransactionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Bank Transactions for a Statement Import",
)
async def list_import_transactions(
    import_public_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    current_admin: AdminUser = require_admin,
    db: AsyncSession = Depends(get_db),
    service: StatementImportService = Depends(get_statement_import_service),
):
    """Fetch paginated list of normalized BankTransaction records created under an import."""
    try:
        return await service.list_import_transactions(
            db=db, import_public_id=import_public_id, page=page, page_size=page_size
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to fetch import transactions.",
        ) from exc
