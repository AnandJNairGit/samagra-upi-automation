"""Pydantic schemas for read-only admin payment dashboard and inspection endpoints."""

import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AdminDashboardSummaryResponse(BaseModel):
    """Summary metrics for the admin dashboard."""

    total_registrations: int = Field(..., description="Total payment sessions / registration attempts")
    pending_payments: int = Field(..., description="Sessions in PENDING state awaiting participant payment")
    submitted_payments: int = Field(..., description="Sessions in SUBMITTED state awaiting admin verification")
    approved_payments: int = Field(..., description="Sessions in APPROVED state")
    rejected_payments: int = Field(..., description="Sessions in REJECTED state")
    total_amount_collected_inr: int = Field(
        ..., description="Sum of amount_inr for APPROVED sessions only (whole INR)"
    )


class AdminPaymentListItem(BaseModel):
    """Payment session summary item for admin payment table."""

    model_config = ConfigDict(from_attributes=True)

    payment_session_public_id: uuid.UUID = Field(..., description="Public UUID of the payment session")
    participant_name: str = Field(..., description="Participant full name")
    phone: str = Field(..., description="Participant phone number")
    email: str = Field(..., description="Participant email address")
    course_public_id: uuid.UUID = Field(..., description="Public UUID of the associated course")
    course_name: str = Field(..., description="Historical course name snapshot")
    batch_public_id: uuid.UUID = Field(..., description="Public UUID of the associated batch")
    batch_name: str = Field(..., description="Historical batch name snapshot")
    amount_inr: int = Field(..., description="Authoritative payment amount in whole INR")
    reference_id: str = Field(..., description="Unique payment reference ID")
    payment_session_status: str = Field(..., description="Current status of the payment session")
    utr: Optional[str] = Field(None, description="Current UTR string if submitted")
    submission_status: Optional[str] = Field(None, description="Status of the current submission")
    submitted_at: Optional[datetime] = Field(None, description="Timestamp of current submission")
    created_at: datetime = Field(..., description="Timestamp when payment session was created")


class AdminPaymentListResponse(BaseModel):
    """Paginated list of payment sessions for admin list view."""

    items: List[AdminPaymentListItem]
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    total: int = Field(..., description="Total matching items count")
    total_pages: int = Field(..., description="Total pages count")


class AdminPaymentDetailParticipant(BaseModel):
    """Participant information for payment detail view."""

    full_name: str
    phone: str
    email: str


class AdminPaymentDetailTraining(BaseModel):
    """Training program historical snapshots for payment detail view."""

    course_public_id: uuid.UUID
    course_name: str
    batch_public_id: uuid.UUID
    batch_name: str


class AdminPaymentDetailPayment(BaseModel):
    """Payment session metadata and financial snapshots for payment detail view."""

    amount_inr: int
    reference_id: str
    upi_id_snapshot: str
    payee_name_snapshot: str
    upi_uri: str
    status: str
    created_at: datetime
    expires_at: Optional[datetime] = None


class AdminPaymentDetailSubmission(BaseModel):
    """Submission item for payment detail view (current or historical)."""

    model_config = ConfigDict(from_attributes=True)

    public_id: uuid.UUID
    utr: str
    status: str
    is_current: bool
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None


class AdminPaymentDetailResponse(BaseModel):
    """Comprehensive read-only payment detail response for administrators."""

    payment_session_public_id: uuid.UUID
    participant: AdminPaymentDetailParticipant
    training: AdminPaymentDetailTraining
    payment: AdminPaymentDetailPayment
    current_submission: Optional[AdminPaymentDetailSubmission] = None
    submission_history: List[AdminPaymentDetailSubmission] = Field(default_factory=list)
