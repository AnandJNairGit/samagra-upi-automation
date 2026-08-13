"""Payment submission database model."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, IdentityIdMixin, PublicIdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.admin_user import AdminUser
    from app.models.payment_session import PaymentSession


class PaymentSubmission(Base, IdentityIdMixin, PublicIdMixin, TimestampMixin):
    """UTR / Transaction submission record for a payment session."""

    __tablename__ = "payment_submissions"

    payment_session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("payment_sessions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    utr: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        default="SUBMITTED",
        nullable=False,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    reviewed_by: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("admin_users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    payment_session: Mapped["PaymentSession"] = relationship(
        "PaymentSession",
        back_populates="submissions",
    )
    reviewer: Mapped[Optional["AdminUser"]] = relationship(
        "AdminUser",
        back_populates="reviewed_submissions",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('SUBMITTED', 'REVIEW_REQUIRED', 'APPROVED', 'REJECTED')",
            name="ck_payment_submissions_status",
        ),
        Index("ux_payment_submissions_utr", "utr", unique=True),
        Index(
            "ux_payment_submissions_current",
            "payment_session_id",
            unique=True,
            postgresql_where=text("is_current = TRUE"),
        ),
        Index("ix_payment_submissions_payment_session", "payment_session_id"),
        Index("ix_payment_submissions_status", "status"),
        Index("ix_payment_submissions_submitted_at", "submitted_at"),
    )
