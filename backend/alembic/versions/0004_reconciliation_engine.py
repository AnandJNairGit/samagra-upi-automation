"""Add reconciliation_runs and reconciliation_results tables for Phase 10 Reconciliation Engine.

Revision ID: 0004_reconciliation_engine
Revises: 0003_statement_imports
Create Date: 2026-08-18 00:00:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic
revision: str = "0004_reconciliation_engine"
down_revision: Union[str, None] = "0003_statement_imports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create reconciliation_runs table
    op.create_table(
        "reconciliation_runs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("public_id", sa.UUID(), nullable=False),
        sa.Column("statement_import_id", sa.BigInteger(), nullable=False),
        sa.Column("initiated_by", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="RUNNING", nullable=False),
        sa.Column("total_transactions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("credit_transactions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("debit_transactions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("matched_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("amount_mismatch_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("unknown_reference_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("no_reference_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("utr_mismatch_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("duplicate_transaction_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("needs_review_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("unmatched_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('RUNNING', 'COMPLETED', 'FAILED')",
            name=op.f("ck_reconciliation_runs_status"),
        ),
        sa.ForeignKeyConstraint(
            ["statement_import_id"],
            ["statement_imports.id"],
            name=op.f("fk_reconciliation_runs_statement_import_id_statement_imports"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["initiated_by"],
            ["admin_users.id"],
            name=op.f("fk_reconciliation_runs_initiated_by_admin_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reconciliation_runs")),
        sa.UniqueConstraint("public_id", name=op.f("ux_reconciliation_runs_public_id")),
    )
    op.create_index("ix_reconciliation_runs_statement_import", "reconciliation_runs", ["statement_import_id"], unique=False)
    op.create_index("ix_reconciliation_runs_initiated_by", "reconciliation_runs", ["initiated_by"], unique=False)
    op.create_index("ix_reconciliation_runs_created_at", "reconciliation_runs", ["created_at"], unique=False)
    op.create_index("ix_reconciliation_runs_status", "reconciliation_runs", ["status"], unique=False)

    # 2. Create reconciliation_results table
    op.create_table(
        "reconciliation_results",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("public_id", sa.UUID(), nullable=False),
        sa.Column("reconciliation_run_id", sa.BigInteger(), nullable=False),
        sa.Column("bank_transaction_id", sa.BigInteger(), nullable=False),
        sa.Column("payment_session_id", sa.BigInteger(), nullable=True),
        sa.Column("payment_submission_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("reference_match", sa.Boolean(), nullable=True),
        sa.Column("amount_match", sa.Boolean(), nullable=True),
        sa.Column("utr_match", sa.Boolean(), nullable=True),
        sa.Column("payer_match", sa.Boolean(), nullable=True),
        sa.Column("reason_code", sa.String(length=50), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('MATCHED', 'AMOUNT_MISMATCH', 'UTR_MISMATCH', 'UNKNOWN_REFERENCE', 'NO_REFERENCE', 'DUPLICATE_TRANSACTION', 'NEEDS_REVIEW', 'UNMATCHED')",
            name=op.f("ck_reconciliation_results_status"),
        ),
        sa.ForeignKeyConstraint(
            ["reconciliation_run_id"],
            ["reconciliation_runs.id"],
            name=op.f("fk_reconciliation_results_reconciliation_run_id_reconciliation_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["bank_transaction_id"],
            ["bank_transactions.id"],
            name=op.f("fk_reconciliation_results_bank_transaction_id_bank_transactions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["payment_session_id"],
            ["payment_sessions.id"],
            name=op.f("fk_reconciliation_results_payment_session_id_payment_sessions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["payment_submission_id"],
            ["payment_submissions.id"],
            name=op.f("fk_reconciliation_results_payment_submission_id_payment_submissions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reconciliation_results")),
        sa.UniqueConstraint("public_id", name=op.f("ux_reconciliation_results_public_id")),
    )
    op.create_index("ix_reconciliation_results_run_id", "reconciliation_results", ["reconciliation_run_id"], unique=False)
    op.create_index("ix_reconciliation_results_bank_tx_id", "reconciliation_results", ["bank_transaction_id"], unique=False)
    op.create_index("ix_reconciliation_results_payment_session_id", "reconciliation_results", ["payment_session_id"], unique=False)
    op.create_index("ix_reconciliation_results_status", "reconciliation_results", ["status"], unique=False)
    op.create_index("ix_reconciliation_results_reason_code", "reconciliation_results", ["reason_code"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_reconciliation_results_reason_code", table_name="reconciliation_results")
    op.drop_index("ix_reconciliation_results_status", table_name="reconciliation_results")
    op.drop_index("ix_reconciliation_results_payment_session_id", table_name="reconciliation_results")
    op.drop_index("ix_reconciliation_results_bank_tx_id", table_name="reconciliation_results")
    op.drop_index("ix_reconciliation_results_run_id", table_name="reconciliation_results")
    op.drop_table("reconciliation_results")

    op.drop_index("ix_reconciliation_runs_status", table_name="reconciliation_runs")
    op.drop_index("ix_reconciliation_runs_created_at", table_name="reconciliation_runs")
    op.drop_index("ix_reconciliation_runs_initiated_by", table_name="reconciliation_runs")
    op.drop_index("ix_reconciliation_runs_statement_import", table_name="reconciliation_runs")
    op.drop_table("reconciliation_runs")
