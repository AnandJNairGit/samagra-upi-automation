"""Batch Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class BatchCreate(BaseModel):
    """Schema for creating a batch (status defaults to ACTIVE, ARCHIVED is forbidden)."""

    course_public_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=200)
    amount_inr: int = Field(..., gt=0, description="Batch fee in whole Indian Rupees (INR)")
    status: str = Field(default="ACTIVE")
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None

    @field_validator("name")
    @classmethod
    def validate_non_blank_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Batch name cannot be empty or whitespace only.")
        return clean

    @field_validator("status")
    @classmethod
    def validate_create_status(cls, v: str) -> str:
        upper = v.upper().strip()
        if upper not in ("ACTIVE", "INACTIVE"):
            raise ValueError("Creation status must be either 'ACTIVE' or 'INACTIVE'. 'ARCHIVED' is not allowed on creation.")
        return upper

    @model_validator(mode="after")
    def validate_date_range(self) -> "BatchCreate":
        if self.starts_at and self.ends_at and self.ends_at < self.starts_at:
            raise ValueError("Batch end date (ends_at) must be on or after start date (starts_at).")
        return self


class BatchUpdate(BaseModel):
    """Schema for updating a batch."""

    course_public_id: Optional[uuid.UUID] = None
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    amount_inr: Optional[int] = Field(None, gt=0)
    status: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None

    @field_validator("name")
    @classmethod
    def validate_non_blank_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            clean = v.strip()
            if not clean:
                raise ValueError("Batch name cannot be empty or whitespace only.")
            return clean
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            upper = v.upper().strip()
            if upper not in ("ACTIVE", "INACTIVE", "ARCHIVED"):
                raise ValueError("Status must be 'ACTIVE', 'INACTIVE', or 'ARCHIVED'.")
            return upper
        return v

    @model_validator(mode="after")
    def validate_date_range(self) -> "BatchUpdate":
        if self.starts_at and self.ends_at and self.ends_at < self.starts_at:
            raise ValueError("Batch end date (ends_at) must be on or after start date (starts_at).")
        return self


class BatchResponse(BaseModel):
    """Public representation of a batch."""

    public_id: uuid.UUID
    course_public_id: uuid.UUID
    course_name: Optional[str] = None
    name: str
    amount_inr: int
    status: str
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

