"""Batch database model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, IdentityIdMixin, PublicIdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.course import Course
    from app.models.payment_session import PaymentSession


class Batch(Base, IdentityIdMixin, PublicIdMixin, TimestampMixin):
    """Cohort / batch under a training program."""

    __tablename__ = "batches"

    course_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("courses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    amount_inr: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        default="ACTIVE",
        nullable=False,
    )
    starts_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ends_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    course: Mapped["Course"] = relationship(
        "Course",
        back_populates="batches",
    )
    payment_sessions: Mapped[List["PaymentSession"]] = relationship(
        "PaymentSession",
        back_populates="batch",
        cascade="none",
    )

    @property
    def course_public_id(self) -> Optional[uuid.UUID]:
        """Expose parent course public UUID if relationship is loaded in session state dict."""
        from sqlalchemy import inspect
        state = inspect(self)
        if "course" in state.dict and state.dict["course"] is not None:
            return state.dict["course"].public_id
        return None

    @property
    def course_name(self) -> Optional[str]:
        """Expose parent course name if relationship is loaded in session state dict."""
        from sqlalchemy import inspect
        state = inspect(self)
        if "course" in state.dict and state.dict["course"] is not None:
            return state.dict["course"].name
        return None



    __table_args__ = (
        CheckConstraint("amount_inr > 0", name="ck_batches_amount_inr"),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED')",
            name="ck_batches_status",
        ),
        CheckConstraint(
            "ends_at IS NULL OR starts_at IS NULL OR ends_at >= starts_at",
            name="ck_batches_date_range",
        ),
        Index("ix_batches_course_id", "course_id"),
        Index("ix_batches_status", "status"),
        Index("ix_batches_course_status", "course_id", "status"),
    )
