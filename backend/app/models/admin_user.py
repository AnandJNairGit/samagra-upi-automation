"""Admin user database model."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, IdentityIdMixin, PublicIdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.payment_submission import PaymentSubmission


class AdminUser(Base, IdentityIdMixin, PublicIdMixin, TimestampMixin):
    """Administrator account model."""

    __tablename__ = "admin_users"

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    reviewed_submissions: Mapped[List["PaymentSubmission"]] = relationship(
        "PaymentSubmission",
        back_populates="reviewer",
        cascade="none",
    )

    __table_args__ = (
        Index(
            "ux_admin_users_email_lower",
            func.lower(email),
            unique=True,
        ),
    )
