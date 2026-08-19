"""Payment submission Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class PaymentSubmissionCreate(BaseModel):
    """Schema for submitting a transaction UTR."""

    utr: Optional[str] = Field(None, min_length=1, max_length=100)

    @field_validator("utr")
    @classmethod
    def validate_non_blank_utr(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip()
        if not clean:
            raise ValueError("utr cannot be empty or whitespace only")
        return clean


class PaymentSubmissionResponse(BaseModel):
    """Internal/Admin representation of a payment submission."""

    public_id: uuid.UUID
    utr: Optional[str] = None
    status: str
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    is_current: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PublicUTRSubmitRequest(BaseModel):
    """Public schema for participant UTR submission.

    Strict Invariants:
        - extra='forbid' prevents client from injecting amounts, statuses, or IDs.
        - Minimum length 4 characters, maximum 100 characters.
        - Trims whitespace and forbids empty or blank string.
    """

    model_config = ConfigDict(extra="forbid")

    utr: Optional[str] = Field(
        None,
        min_length=4,
        max_length=100,
        description="Bank / UPI transaction reference (UTR) number — optional, submit if available",
    )

    @field_validator("utr")
    @classmethod
    def validate_utr(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip()
        if not clean:
            return None  # Treat empty string as absent
        if len(clean) < 4:
            raise ValueError("Transaction reference (UTR) must be at least 4 characters long.")
        if len(clean) > 100:
            raise ValueError("Transaction reference (UTR) cannot exceed 100 characters.")
        return clean


class PublicUTRSubmitResponse(BaseModel):
    """Public response returned upon successful UTR submission."""

    model_config = ConfigDict(from_attributes=True)

    payment_session_public_id: uuid.UUID
    submission_public_id: uuid.UUID
    status: str
    utr_masked: Optional[str] = None
    submitted_at: datetime
    whatsapp_url: str
