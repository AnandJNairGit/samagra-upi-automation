"""Public registration request and response validation schemas."""

import re
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


INDIAN_PHONE_REGEX = re.compile(r"^[6-9]\d{9}$")


class PublicBatchResponse(BaseModel):
    """Minimal, unauthenticated public view of an active cohort."""

    model_config = ConfigDict(from_attributes=True)

    public_id: uuid.UUID
    course_name: str
    batch_name: str
    amount_inr: int
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


class PublicRegistrationValidateRequest(BaseModel):
    """Participant registration submission for validation prior to Phase 6 payment handoff."""

    model_config = ConfigDict(extra="forbid")  # Rejects unexpected client fields like amount_inr or course_id

    batch_public_id: uuid.UUID
    full_name: str = Field(..., min_length=2, max_length=255, description="Full name of participant")
    phone: str = Field(..., description="10-digit Indian mobile number")
    email: EmailStr = Field(..., description="Valid contact email address")

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        clean = v.strip()
        if len(clean) < 2:
            raise ValueError("Full name must be at least 2 characters long.")
        if len(clean) > 255:
            raise ValueError("Full name cannot exceed 255 characters.")
        return clean

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Strip common formatting characters (+91 prefix, leading 0, spaces, dashes)
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


class PublicRegistrationValidateResponse(BaseModel):
    """Authoritative validated registration context returned to the client and Phase 6 handoff."""

    model_config = ConfigDict(from_attributes=True)

    batch_public_id: uuid.UUID
    course_name: str
    batch_name: str
    amount_inr: int
    full_name: str
    phone: str
    email: str
