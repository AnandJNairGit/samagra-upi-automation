"""Pydantic schemas for reconciliation engine requests and responses."""

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ReconciliationRunCreateRequest(BaseModel):
    """Payload to initiate a batch-scoped reconciliation run against an imported statement."""

    model_config = ConfigDict(extra="forbid")

    batch_public_id: uuid.UUID = Field(
        ...,
        description="Public UUID of the batch being reconciled.",
    )
    statement_import_public_id: uuid.UUID = Field(
        ...,
        description="Public UUID of the completed statement import file.",
    )


class ReconciliationRunResponse(BaseModel):
    """Response DTO representing a reconciliation execution run."""

    public_id: uuid.UUID
    statement_import_public_id: uuid.UUID
    batch_public_id: Optional[uuid.UUID] = None
    filename: str
    batch_name: Optional[str] = None
    status: str

    total_transactions: int
    credit_transactions: int
    debit_transactions: int

    matched_count: int
    amount_mismatch_count: int
    unknown_reference_count: int
    no_reference_count: int
    utr_mismatch_count: int
    duplicate_transaction_count: int
    needs_review_count: int
    unmatched_count: int

    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReconciliationRunListResponse(BaseModel):
    """Paginated list response of reconciliation runs."""

    items: List[ReconciliationRunResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ReconciliationResultResponse(BaseModel):
    """Response DTO for an individual reconciliation classification result."""

    public_id: uuid.UUID
    reconciliation_run_public_id: uuid.UUID
    bank_transaction_public_id: uuid.UUID
    payment_session_public_id: Optional[uuid.UUID] = None
    payment_submission_public_id: Optional[uuid.UUID] = None

    status: str
    reason_code: str
    explanation: str

    # Evaluation flags
    reference_match: Optional[bool] = None
    amount_match: Optional[bool] = None
    utr_match: Optional[bool] = None
    payer_match: Optional[bool] = None

    # Key fields for quick table view
    bank_reference_id: Optional[str] = None
    bank_amount_inr: Optional[int] = None
    bank_utr: Optional[str] = None
    bank_transaction_at: Optional[datetime] = None
    bank_counterparty_name: Optional[str] = None

    expected_reference_id: Optional[str] = None
    expected_amount_inr: Optional[int] = None
    submitted_utr: Optional[str] = None
    participant_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ReconciliationResultDetailResponse(ReconciliationResultResponse):
    """Detailed inspection record for a single reconciliation result."""

    statement_filename: str
    bank_direction: Optional[str] = None
    bank_description: Optional[str] = None
    payment_session_status: Optional[str] = None
    course_name_snapshot: Optional[str] = None
    batch_name_snapshot: Optional[str] = None
    submission_status: Optional[str] = None
    submitted_at: Optional[datetime] = None


class ReconciliationResultListResponse(BaseModel):
    """Paginated list response of reconciliation results for a run."""

    items: List[ReconciliationResultResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
