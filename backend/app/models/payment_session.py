"""Payment session database model."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, IdentityIdMixin, PublicIdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.batch import Batch
    from app.models.course import Course
    from app.models.payment_submission import PaymentSubmission


class PaymentSession(Base, IdentityIdMixin, PublicIdMixin, TimestampMixin):
    """Payment session representing a single participant checkout intent."""

    __tablename__ = "payment_sessions"

    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)

    course_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("courses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    batch_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("batches.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Immutable historical snapshots
    course_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    batch_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    amount_inr: Mapped[int] = mapped_column(BigInteger, nullable=False)

    reference_id: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        nullable=False,
    )

    # Historical UPI snapshots
    upi_id_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    payee_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    upi_uri: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
        nullable=False,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    course: Mapped["Course"] = relationship(
        "Course",
        back_populates="payment_sessions",
    )
    batch: Mapped["Batch"] = relationship(
        "Batch",
        back_populates="payment_sessions",
    )
    submissions: Mapped[List["PaymentSubmission"]] = relationship(
        "PaymentSubmission",
        back_populates="payment_session",
        cascade="none",
    )

    __table_args__ = (
        CheckConstraint("amount_inr > 0", name="ck_payment_sessions_amount_inr"),
        CheckConstraint(
            "status IN ('PENDING', 'SUBMITTED', 'REVIEW_REQUIRED', 'APPROVED', 'REJECTED', 'EXPIRED')",
            name="ck_payment_sessions_status",
        ),
        Index("ix_payment_sessions_status", "status"),
        Index("ix_payment_sessions_phone", "phone"),
        Index("ix_payment_sessions_created_at", "created_at"),
        Index("ix_payment_sessions_batch_status", "batch_id", "status"),
    )
