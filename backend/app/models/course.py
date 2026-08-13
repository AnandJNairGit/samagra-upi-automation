"""Course database model."""

from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import CheckConstraint, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, IdentityIdMixin, PublicIdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.batch import Batch
    from app.models.payment_session import PaymentSession


class Course(Base, IdentityIdMixin, PublicIdMixin, TimestampMixin):
    """Training program course entity."""

    __tablename__ = "courses"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default="ACTIVE",
        nullable=False,
    )

    # Relationships
    batches: Mapped[List["Batch"]] = relationship(
        "Batch",
        back_populates="course",
        cascade="none",
    )
    payment_sessions: Mapped[List["PaymentSession"]] = relationship(
        "PaymentSession",
        back_populates="course",
        cascade="none",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED')",
            name="ck_courses_status",
        ),
        Index("ix_courses_status", "status"),
    )
