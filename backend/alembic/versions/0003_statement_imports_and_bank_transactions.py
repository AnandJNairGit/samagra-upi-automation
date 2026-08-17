"""Add statement_imports and bank_transactions tables for Phase 9 statement import.

Revision ID: 0003_statement_imports_and_bank_transactions
Revises: 0002_admin_sessions
Create Date: 2026-08-17 15:15:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic
revision: str = "0003_statement_imports"
down_revision: Union[str, None] = "0002_admin_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create statement_imports table
    op.create_table(
        "statement_imports",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("public_id", sa.UUID(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=20), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("file_checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("canonical_mapping_hash", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=50), server_default="GOOGLE_PAY", nullable=False),
        sa.Column("selected_sheet_name", sa.String(length=100), nullable=True),
        sa.Column("header_row_index", sa.Integer(), server_default="1", nullable=False),
        sa.Column("column_mapping", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="COMPLETED", nullable=False),
        sa.Column("total_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("valid_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("invalid_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("duplicate_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("new_transactions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rows_without_reference", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("imported_by", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("file_size >= 0", name=op.f("ck_statement_imports_file_size")),
        sa.CheckConstraint("status IN ('COMPLETED', 'COMPLETED_WITH_ERRORS', 'FAILED')", name=op.f("ck_statement_imports_status")),
        sa.ForeignKeyConstraint(
            ["imported_by"],
            ["admin_users.id"],
            name=op.f("fk_statement_imports_imported_by_admin_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_statement_imports")),
        sa.UniqueConstraint("public_id", name=op.f("ux_statement_imports_public_id")),
    )
    op.create_index("ix_statement_imports_checksum", "statement_imports", ["file_checksum_sha256"], unique=False)
    op.create_index("ix_statement_imports_canonical_hash", "statement_imports", ["canonical_mapping_hash"], unique=False)
    op.create_index("ix_statement_imports_created_at", "statement_imports", ["created_at"], unique=False)
    op.create_index("ix_statement_imports_imported_by", "statement_imports", ["imported_by"], unique=False)

    # 2. Create bank_transactions table
    op.create_table(
        "bank_transactions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("public_id", sa.UUID(), nullable=False),
        sa.Column("statement_import_id", sa.BigInteger(), nullable=False),
        sa.Column("transaction_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("amount_inr", sa.BigInteger(), nullable=True),
        sa.Column("direction", sa.String(length=10), nullable=True),
        sa.Column("reference_id", sa.String(length=100), nullable=True),
        sa.Column("utr", sa.String(length=100), nullable=True),
        sa.Column("counterparty_name", sa.String(length=250), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=50), server_default="GOOGLE_PAY", nullable=False),
        sa.Column("source_transaction_key", sa.String(length=255), nullable=True),
        sa.Column("raw_row_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["statement_import_id"],
            ["statement_imports.id"],
            name=op.f("fk_bank_transactions_statement_import_id_statement_imports"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bank_transactions")),
        sa.UniqueConstraint("public_id", name=op.f("ux_bank_transactions_public_id")),
    )
    op.create_index("ix_bank_transactions_statement_import", "bank_transactions", ["statement_import_id"], unique=False)
    op.create_index("ix_bank_transactions_reference_id", "bank_transactions", ["reference_id"], unique=False)
    op.create_index("ix_bank_transactions_utr", "bank_transactions", ["utr"], unique=False)
    op.create_index("ix_bank_transactions_transaction_at", "bank_transactions", ["transaction_at"], unique=False)
    op.create_index("ix_bank_transactions_amount_inr", "bank_transactions", ["amount_inr"], unique=False)
    op.create_index(
        "ux_bank_transactions_source_key",
        "bank_transactions",
        ["source", "source_transaction_key"],
        unique=True,
        postgresql_where=sa.text("source_transaction_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ux_bank_transactions_source_key", table_name="bank_transactions")
    op.drop_index("ix_bank_transactions_amount_inr", table_name="bank_transactions")
    op.drop_index("ix_bank_transactions_transaction_at", table_name="bank_transactions")
    op.drop_index("ix_bank_transactions_utr", table_name="bank_transactions")
    op.drop_index("ix_bank_transactions_reference_id", table_name="bank_transactions")
    op.drop_index("ix_bank_transactions_statement_import", table_name="bank_transactions")
    op.drop_table("bank_transactions")

    op.drop_index("ix_statement_imports_imported_by", table_name="statement_imports")
    op.drop_index("ix_statement_imports_created_at", table_name="statement_imports")
    op.drop_index("ix_statement_imports_canonical_hash", table_name="statement_imports")
    op.drop_index("ix_statement_imports_checksum", table_name="statement_imports")
    op.drop_table("statement_imports")
