"""Add batch_id column to reconciliation_runs table for batch-scoped reconciliation workflow.

Revision ID: 0005_reconciliation_batch_id
Revises: 0004_reconciliation_engine
Create Date: 2026-08-18 14:30:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic
revision: str = "0005_reconciliation_batch_id"
down_revision: Union[str, None] = "0004_reconciliation_engine"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "reconciliation_runs",
        sa.Column("batch_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_reconciliation_runs_batch_id_batches"),
        "reconciliation_runs",
        "batches",
        ["batch_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_reconciliation_runs_batch_id",
        "reconciliation_runs",
        ["batch_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_reconciliation_runs_batch_id", table_name="reconciliation_runs")
    op.drop_constraint(
        op.f("fk_reconciliation_runs_batch_id_batches"),
        "reconciliation_runs",
        type_="foreignkey",
    )
    op.drop_column("reconciliation_runs", "batch_id")
