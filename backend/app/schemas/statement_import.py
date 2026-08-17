"""Pydantic request and response schemas for statement imports and bank transactions."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator


class ColumnFieldMapping(BaseModel):
    """Mapping for a single normalized target field to a source column index."""
    model_config = ConfigDict(extra="forbid")

    column_index: int = Field(..., ge=0, description="0-based index of source column")
    header: Optional[str] = Field(None, description="Human-readable header label for auditability")


class StatementColumnMapping(BaseModel):
    """Complete column mapping configuration provided by administrator."""
    model_config = ConfigDict(extra="forbid")

    reference_id: ColumnFieldMapping = Field(..., description="System-generated payment Reference Code column")
    amount: ColumnFieldMapping = Field(..., description="Transaction amount column")
    transaction_at: Optional[ColumnFieldMapping] = Field(None, description="Transaction date/time column")
    direction: Optional[ColumnFieldMapping] = Field(None, description="Transaction type / direction (CREDIT/DEBIT) column")
    utr: Optional[ColumnFieldMapping] = Field(None, description="Optional UTR / Bank Ref ID column")
    counterparty_name: Optional[ColumnFieldMapping] = Field(None, description="Optional Payer / Counterparty name column")
    description: Optional[ColumnFieldMapping] = Field(None, description="Optional remarks / description column")


class HeaderItem(BaseModel):
    """Header representation returning column index and label."""
    model_config = ConfigDict(extra="ignore")

    column_index: int
    header: str


class ImportPreviewResponse(BaseModel):
    """Response returned after initial file upload & inspection."""
    model_config = ConfigDict(extra="ignore")

    preview_token: str
    filename: str
    file_type: str  # csv, xlsx
    file_size: int
    file_checksum_sha256: str
    available_sheets: List[str]
    selected_sheet_name: Optional[str] = None
    header_row_index: int
    headers: List[HeaderItem]
    preview_rows: List[Dict[str, Any]]
    total_detected_rows: int
    expires_in_seconds: int = 1800


class ImportConfirmRequest(BaseModel):
    """Payload for confirming statement import with mapped columns."""
    model_config = ConfigDict(extra="forbid")

    preview_token: str = Field(..., min_length=1, description="Opaque preview token from upload step")
    sheet_name: Optional[str] = Field(None, description="Selected worksheet name for Excel files")
    header_row_index: int = Field(1, ge=1, description="1-indexed row number containing column headers")
    column_mapping: StatementColumnMapping = Field(..., description="Position-based column mapping configuration")
    source_timezone: Optional[str] = Field(None, description="Timezone name if timestamps are naive (defaults to Asia/Kolkata)")


class ImportSummaryResponse(BaseModel):
    """Summary metrics returned after confirming import execution."""
    model_config = ConfigDict(extra="ignore")

    already_imported: bool = False
    import_public_id: uuid.UUID
    filename: str
    file_type: str
    selected_sheet_name: Optional[str] = None
    status: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    new_transactions: int
    rows_without_reference: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_summary: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


class StatementImportListItemResponse(BaseModel):
    """Summary item for import history list."""
    model_config = ConfigDict(from_attributes=True)

    public_id: uuid.UUID
    filename: str
    file_type: str
    source: str
    selected_sheet_name: Optional[str] = None
    status: str
    total_rows: int
    valid_rows: int
    duplicate_rows: int
    new_transactions: int
    rows_without_reference: int
    imported_by_name: str
    created_at: datetime


class StatementImportListResponse(BaseModel):
    """Paginated list response for statement import history."""
    model_config = ConfigDict(extra="ignore")

    items: List[StatementImportListItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class StatementImportDetailResponse(BaseModel):
    """Detailed audit view for a completed statement import."""
    model_config = ConfigDict(from_attributes=True)

    public_id: uuid.UUID
    filename: str
    file_type: str
    file_size: int
    file_checksum_sha256: str
    canonical_mapping_hash: str
    source: str
    selected_sheet_name: Optional[str] = None
    header_row_index: int
    column_mapping: Dict[str, Any]
    status: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    new_transactions: int
    rows_without_reference: int
    error_summary: Optional[Dict[str, Any]] = None
    imported_by_name: str
    created_at: datetime
    completed_at: Optional[datetime] = None


class BankTransactionResponse(BaseModel):
    """Public/Admin view for an imported bank transaction (omits raw_row_data for privacy)."""
    model_config = ConfigDict(from_attributes=True)

    public_id: uuid.UUID
    transaction_at: Optional[datetime] = None
    amount_inr: Optional[int] = None
    direction: Optional[str] = None
    reference_id: Optional[str] = None
    utr: Optional[str] = None
    counterparty_name: Optional[str] = None
    description: Optional[str] = None
    source: str
    source_transaction_key: Optional[str] = None
    created_at: datetime


class BankTransactionListResponse(BaseModel):
    """Paginated list response for bank transactions under an import."""
    model_config = ConfigDict(extra="ignore")

    items: List[BankTransactionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
