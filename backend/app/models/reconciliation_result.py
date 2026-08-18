"""Reconciliation result database model for tracking individual transaction classifications."""

from typing import TYPE_CHECKING, Optional
from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, IdentityIdMixin, PublicIdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.bank_transaction import BankTransaction
    from app.models.payment_session import PaymentSession
    from app.models.payment_submission import PaymentSubmission
    from app.models.reconciliation_run import ReconciliationRun


class ReconciliationResult(Base, IdentityIdMixin, PublicIdMixin, TimestampMixin):
    """Reconciliation result record representing the classification of a single bank transaction."""

    __tablename__ = "reconciliation_results"

    reconciliation_run_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("reconciliation_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    bank_transaction_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("bank_transactions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    payment_session_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("payment_sessions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    payment_submission_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("payment_submissions.id", ondelete="RESTRICT"),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )  # MATCHED, AMOUNT_MISMATCH, UTR_MISMATCH, UNKNOWN_REFERENCE, NO_REFERENCE, DUPLICATE_TRANSACTION, NEEDS_REVIEW, UNMATCHED

    reference_match: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    amount_match: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    utr_match: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    payer_match: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    reason_code: Mapped[str] = mapped_column(String(50), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    reconciliation_run: Mapped["ReconciliationRun"] = relationship(
        "ReconciliationRun",
        back_populates="results",
    )
    bank_transaction: Mapped["BankTransaction"] = relationship(
        "BankTransaction",
    )
    payment_session: Mapped[Optional["PaymentSession"]] = relationship(
        "PaymentSession",
    )
    payment_submission: Mapped[Optional["PaymentSubmission"]] = relationship(
        "PaymentSubmission",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('MATCHED', 'AMOUNT_MISMATCH', 'UTR_MISMATCH', 'UNKNOWN_REFERENCE', 'NO_REFERENCE', 'DUPLICATE_TRANSACTION', 'NEEDS_REVIEW', 'UNMATCHED')",
            name="ck_reconciliation_results_status",
        ),
        Index("ix_reconciliation_results_run_id", "reconciliation_run_id"),
        Index("ix_reconciliation_results_bank_tx_id", "bank_transaction_id"),
        Index("ix_reconciliation_results_payment_session_id", "payment_session_id"),
        Index("ix_reconciliation_results_status", "status"),
        Index("ix_reconciliation_results_reason_code", "reason_code"),
    )
