"""Payment session Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class PaymentSessionCreate(BaseModel):
    """Schema for initiating a payment session."""

    full_name: str = Field(..., min_length=1, max_length=150)
    phone: str = Field(..., min_length=5, max_length=20)
    email: EmailStr
    course_public_id: uuid.UUID
    batch_public_id: uuid.UUID

    @field_validator("full_name")
    @classmethod
    def validate_non_blank_full_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("full_name cannot be empty or whitespace only")
        return clean

    @field_validator("phone")
    @classmethod
    def validate_non_blank_phone(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("phone cannot be empty or whitespace only")
        return clean


class PaymentSessionResponse(BaseModel):
    """Public representation of a payment session."""

    public_id: uuid.UUID
    full_name: str
    phone: str
    email: str

    course_name_snapshot: str
    batch_name_snapshot: str
    amount_inr: int

    reference_id: str
    upi_id_snapshot: str
    payee_name_snapshot: str
    upi_uri: str

    status: str
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
