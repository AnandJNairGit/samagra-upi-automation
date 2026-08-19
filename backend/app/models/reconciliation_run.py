"""Reconciliation run database model for tracking automated execution runs against bank statements."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, IdentityIdMixin, PublicIdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.admin_user import AdminUser
    from app.models.batch import Batch
    from app.models.reconciliation_result import ReconciliationResult
    from app.models.statement_import import StatementImport


class ReconciliationRun(Base, IdentityIdMixin, PublicIdMixin, TimestampMixin):
    """Reconciliation run record representing an execution pass evaluating statement transactions."""

    __tablename__ = "reconciliation_runs"

    statement_import_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("statement_imports.id", ondelete="RESTRICT"),
        nullable=False,
    )
    batch_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("batches.id", ondelete="RESTRICT"),
        nullable=True,
    )
    initiated_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("admin_users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="RUNNING",
        nullable=False,
    )  # RUNNING, COMPLETED, FAILED

    total_transactions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    credit_transactions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    debit_transactions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    matched_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    amount_mismatch_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unknown_reference_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    no_reference_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    utr_mismatch_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_transaction_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    needs_review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unmatched_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    statement_import: Mapped["StatementImport"] = relationship(
        "StatementImport",
    )
    batch: Mapped[Optional["Batch"]] = relationship(
        "Batch",
    )
    admin_user: Mapped["AdminUser"] = relationship(
        "AdminUser",
    )
    results: Mapped[List["ReconciliationResult"]] = relationship(
        "ReconciliationResult",
        back_populates="reconciliation_run",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('RUNNING', 'COMPLETED', 'FAILED')",
            name="ck_reconciliation_runs_status",
        ),
        Index("ix_reconciliation_runs_statement_import", "statement_import_id"),
        Index("ix_reconciliation_runs_batch_id", "batch_id"),
        Index("ix_reconciliation_runs_initiated_by", "initiated_by"),
        Index("ix_reconciliation_runs_created_at", "created_at"),
        Index("ix_reconciliation_runs_status", "status"),
    )

