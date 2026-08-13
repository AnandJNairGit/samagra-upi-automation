"""SQLAlchemy 2.x Declarative Base and foundational mixins."""

import uuid
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, Identity, MetaData, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Explicit naming conventions for constraints and indexes
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "ux_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative Base with custom metadata naming conventions."""

    metadata = MetaData(naming_convention=convention)


class TimestampMixin:
    """Provides UTC timestamp columns for creation and modification tracking."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class IdentityIdMixin:
    """Provides standard BIGINT identity primary key."""

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )


class PublicIdMixin:
    """Provides public UUID identifier for safe external exposure."""

    public_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
