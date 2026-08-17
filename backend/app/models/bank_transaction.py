"""Bank transaction database model for normalized statement transaction rows."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, IdentityIdMixin, PublicIdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.statement_import import StatementImport


class BankTransaction(Base, IdentityIdMixin, PublicIdMixin, TimestampMixin):
    """Bank transaction record representing a normalized row imported from a statement."""

    __tablename__ = "bank_transactions"

    statement_import_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("statement_imports.id", ondelete="RESTRICT"),
        nullable=False,
    )

    transaction_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    amount_inr: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True,
    )
    direction: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
    )  # CREDIT, DEBIT

    reference_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    utr: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    counterparty_name: Mapped[Optional[str]] = mapped_column(
        String(250),
        nullable=True,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    source: Mapped[str] = mapped_column(
        String(50),
        default="GOOGLE_PAY",
        nullable=False,
    )
    source_transaction_key: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    raw_row_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Relationships
    statement_import: Mapped["StatementImport"] = relationship(
        "StatementImport",
        back_populates="bank_transactions",
    )

    __table_args__ = (
        Index("ix_bank_transactions_statement_import", "statement_import_id"),
        Index("ix_bank_transactions_reference_id", "reference_id"),
        Index("ix_bank_transactions_utr", "utr"),
        Index("ix_bank_transactions_transaction_at", "transaction_at"),
        Index("ix_bank_transactions_amount_inr", "amount_inr"),
        Index(
            "ux_bank_transactions_source_key",
            "source",
            "source_transaction_key",
            unique=True,
            postgresql_where=(source_transaction_key.isnot(None)),
        ),
    )
