"""Payment session Pydantic validation schemas for Phase 6 UPI checkout."""

import re
import uuid
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


INDIAN_PHONE_REGEX = re.compile(r"^[6-9]\d{9}$")


class PaymentSessionCreateRequest(BaseModel):
    """Public participant checkout initiation request for a batch.

    Strict Invariant:
        extra='forbid' prevents client from injecting amounts, courses, reference IDs, or UPI IDs.
    """

    model_config = ConfigDict(extra="forbid")

    batch_public_id: uuid.UUID
    full_name: str = Field(..., min_length=2, max_length=150, description="Full name of participant")
    phone: str = Field(..., description="10-digit Indian mobile number")
    email: EmailStr = Field(..., description="Valid contact email address")

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        clean = v.strip()
        if len(clean) < 2:
            raise ValueError("Full name must be at least 2 characters long.")
        if len(clean) > 150:
            raise ValueError("Full name cannot exceed 150 characters.")
        return clean

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        clean = re.sub(r"[\s\-\(\)]", "", v.strip())
        if clean.startswith("+91"):
            clean = clean[3:]
        elif clean.startswith("91") and len(clean) == 12:
            clean = clean[2:]
        elif clean.startswith("0") and len(clean) == 11:
            clean = clean[1:]

        if not INDIAN_PHONE_REGEX.match(clean):
            raise ValueError("Please enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9.")
        return clean

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: EmailStr) -> str:
        return str(v).strip().lower()


class PaymentSessionPublicResponse(BaseModel):
    """Safe public representation of a payment session for rendering the payment page."""

    model_config = ConfigDict(from_attributes=True)

    public_id: uuid.UUID
    full_name: str
    phone: str
    email: str

    course_name: str
    batch_name: str
    amount_inr: int

    reference_id: str
    upi_id: str
    payee_name: str
    upi_uri: str

    status: str
    expires_at: Optional[datetime] = None
    is_expired: bool = False
    created_at: datetime

    @classmethod
    def from_orm_model(cls, model) -> "PaymentSessionPublicResponse":
        """Construct public response from SQLAlchemy PaymentSession model instance."""
        now = datetime.now(timezone.utc)
        expired = bool(model.expires_at and model.expires_at < now and model.status == "PENDING")

        return cls(
            public_id=model.public_id,
            full_name=model.full_name,
            phone=model.phone,
            email=model.email,
            course_name=model.course_name_snapshot,
            batch_name=model.batch_name_snapshot,
            amount_inr=model.amount_inr,
            reference_id=model.reference_id,
            upi_id=model.upi_id_snapshot,
            payee_name=model.payee_name_snapshot,
            upi_uri=model.upi_uri,
            status="EXPIRED" if expired else model.status,
            expires_at=model.expires_at,
            is_expired=expired,
            created_at=model.created_at,
        )
