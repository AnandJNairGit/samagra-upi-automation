"""Admin session database model for refresh token tracking and rotation."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, IdentityIdMixin, PublicIdMixin

if TYPE_CHECKING:
    from app.models.admin_user import AdminUser


class AdminSession(Base, IdentityIdMixin, PublicIdMixin):
    """Administrator session representing a login device / refresh token lifecycle."""

    __tablename__ = "admin_sessions"

    admin_user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("admin_users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    refresh_token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        INET,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    admin_user: Mapped["AdminUser"] = relationship(
        "AdminUser",
        back_populates="sessions",
    )

    __table_args__ = (
        Index("ux_admin_sessions_refresh_token_hash", "refresh_token_hash", unique=True),
        Index("ix_admin_sessions_admin_user_revoked", "admin_user_id", "revoked_at"),
        Index("ix_admin_sessions_expires_at", "expires_at"),
    )
