"""Payment submission Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class PaymentSubmissionCreate(BaseModel):
    """Schema for submitting a transaction UTR."""

    utr: str = Field(..., min_length=1, max_length=100)

    @field_validator("utr")
    @classmethod
    def validate_non_blank_utr(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("utr cannot be empty or whitespace only")
        return clean


class PaymentSubmissionResponse(BaseModel):
    """Public representation of a payment submission."""

    public_id: uuid.UUID
    utr: str
    status: str
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    is_current: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
