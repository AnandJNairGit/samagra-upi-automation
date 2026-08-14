"""Add admin_sessions table for Phase 3 authentication and refresh token rotation.

Revision ID: 0002_admin_sessions
Revises: 0001_initial_phase2_schema
Create Date: 2026-08-13 19:30:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic
revision: str = "0002_admin_sessions"
down_revision: Union[str, None] = "0001_initial_phase2_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_sessions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("public_id", sa.UUID(), nullable=False),
        sa.Column("admin_user_id", sa.BigInteger(), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["admin_user_id"],
            ["admin_users.id"],
            name=op.f("fk_admin_sessions_admin_user_id_admin_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_admin_sessions")),
        sa.UniqueConstraint("public_id", name=op.f("ux_admin_sessions_public_id")),
    )
    op.create_index(
        "ux_admin_sessions_refresh_token_hash",
        "admin_sessions",
        ["refresh_token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_admin_sessions_admin_user_revoked",
        "admin_sessions",
        ["admin_user_id", "revoked_at"],
        unique=False,
    )
    op.create_index(
        "ix_admin_sessions_expires_at",
        "admin_sessions",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_admin_sessions_expires_at", table_name="admin_sessions")
    op.drop_index("ix_admin_sessions_admin_user_revoked", table_name="admin_sessions")
    op.drop_index("ux_admin_sessions_refresh_token_hash", table_name="admin_sessions")
    op.drop_table("admin_sessions")
