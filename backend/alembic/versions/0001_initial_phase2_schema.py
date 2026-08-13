"""Initial Phase 2 schema migration.

Revision ID: 0001_initial_phase2_schema
Revises:
Create Date: 2026-08-13 16:30:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic
revision: str = "0001_initial_phase2_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # 1. admin_users
    # -------------------------------------------------------------------------
    op.create_table(
        "admin_users",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("public_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_admin_users")),
        sa.UniqueConstraint("public_id", name=op.f("ux_admin_users_public_id")),
    )
    op.create_index(
        "ux_admin_users_email_lower",
        "admin_users",
        [sa.text("LOWER(email)")],
        unique=True,
    )

    # -------------------------------------------------------------------------
    # 2. courses
    # -------------------------------------------------------------------------
    op.create_table(
        "courses",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("public_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="ACTIVE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED')", name=op.f("ck_courses_status")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_courses")),
        sa.UniqueConstraint("public_id", name=op.f("ux_courses_public_id")),
    )
    op.create_index("ix_courses_status", "courses", ["status"], unique=False)

    # -------------------------------------------------------------------------
    # 3. batches
    # -------------------------------------------------------------------------
    op.create_table(
        "batches",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("public_id", sa.UUID(), nullable=False),
        sa.Column("course_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("amount_inr", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="ACTIVE", nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("amount_inr > 0", name=op.f("ck_batches_amount_inr")),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE', 'ARCHIVED')", name=op.f("ck_batches_status")),
        sa.CheckConstraint("ends_at IS NULL OR starts_at IS NULL OR ends_at >= starts_at", name=op.f("ck_batches_date_range")),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name=op.f("fk_batches_course_id_courses"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_batches")),
        sa.UniqueConstraint("public_id", name=op.f("ux_batches_public_id")),
    )
    op.create_index("ix_batches_course_id", "batches", ["course_id"], unique=False)
    op.create_index("ix_batches_status", "batches", ["status"], unique=False)
    op.create_index("ix_batches_course_status", "batches", ["course_id", "status"], unique=False)

    # -------------------------------------------------------------------------
    # 4. payment_sessions
    # -------------------------------------------------------------------------
    op.create_table(
        "payment_sessions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("public_id", sa.UUID(), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("course_id", sa.BigInteger(), nullable=False),
        sa.Column("batch_id", sa.BigInteger(), nullable=False),
        sa.Column("course_name_snapshot", sa.String(length=200), nullable=False),
        sa.Column("batch_name_snapshot", sa.String(length=200), nullable=False),
        sa.Column("amount_inr", sa.BigInteger(), nullable=False),
        sa.Column("reference_id", sa.String(length=40), nullable=False),
        sa.Column("upi_id_snapshot", sa.String(length=100), nullable=False),
        sa.Column("payee_name_snapshot", sa.String(length=200), nullable=False),
        sa.Column("upi_uri", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="PENDING", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint("amount_inr > 0", name=op.f("ck_payment_sessions_amount_inr")),
        sa.CheckConstraint(
            "status IN ('PENDING', 'SUBMITTED', 'REVIEW_REQUIRED', 'APPROVED', 'REJECTED', 'EXPIRED')",
            name=op.f("ck_payment_sessions_status"),
        ),
        sa.ForeignKeyConstraint(["batch_id"], ["batches.id"], name=op.f("fk_payment_sessions_batch_id_batches"), ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name=op.f("fk_payment_sessions_course_id_courses"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payment_sessions")),
        sa.UniqueConstraint("public_id", name=op.f("ux_payment_sessions_public_id")),
        sa.UniqueConstraint("reference_id", name=op.f("ux_payment_sessions_reference_id")),
    )
    op.create_index("ix_payment_sessions_status", "payment_sessions", ["status"], unique=False)
    op.create_index("ix_payment_sessions_phone", "payment_sessions", ["phone"], unique=False)
    op.create_index("ix_payment_sessions_created_at", "payment_sessions", ["created_at"], unique=False)
    op.create_index("ix_payment_sessions_batch_status", "payment_sessions", ["batch_id", "status"], unique=False)

    # -------------------------------------------------------------------------
    # 5. payment_submissions
    # -------------------------------------------------------------------------
    op.create_table(
        "payment_submissions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("public_id", sa.UUID(), nullable=False),
        sa.Column("payment_session_id", sa.BigInteger(), nullable=False),
        sa.Column("utr", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="SUBMITTED", nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("reviewed_by", sa.BigInteger(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('SUBMITTED', 'REVIEW_REQUIRED', 'APPROVED', 'REJECTED')",
            name=op.f("ck_payment_submissions_status"),
        ),
        sa.ForeignKeyConstraint(
            ["payment_session_id"],
            ["payment_sessions.id"],
            name=op.f("fk_payment_submissions_payment_session_id_payment_sessions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["admin_users.id"],
            name=op.f("fk_payment_submissions_reviewed_by_admin_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payment_submissions")),
        sa.UniqueConstraint("public_id", name=op.f("ux_payment_submissions_public_id")),
    )
    op.create_index("ux_payment_submissions_utr", "payment_submissions", ["utr"], unique=True)
    op.create_index(
        "ux_payment_submissions_current",
        "payment_submissions",
        ["payment_session_id"],
        unique=True,
        postgresql_where=sa.text("is_current = TRUE"),
    )
    op.create_index("ix_payment_submissions_payment_session", "payment_submissions", ["payment_session_id"], unique=False)
    op.create_index("ix_payment_submissions_status", "payment_submissions", ["status"], unique=False)
    op.create_index("ix_payment_submissions_submitted_at", "payment_submissions", ["submitted_at"], unique=False)


def downgrade() -> None:
    # -------------------------------------------------------------------------
    # Downgrade in reverse dependency order
    # -------------------------------------------------------------------------
    op.drop_index("ix_payment_submissions_submitted_at", table_name="payment_submissions")
    op.drop_index("ix_payment_submissions_status", table_name="payment_submissions")
    op.drop_index("ix_payment_submissions_payment_session", table_name="payment_submissions")
    op.drop_index("ux_payment_submissions_current", table_name="payment_submissions")
    op.drop_index("ux_payment_submissions_utr", table_name="payment_submissions")
    op.drop_table("payment_submissions")

    op.drop_index("ix_payment_sessions_batch_status", table_name="payment_sessions")
    op.drop_index("ix_payment_sessions_created_at", table_name="payment_sessions")
    op.drop_index("ix_payment_sessions_phone", table_name="payment_sessions")
    op.drop_index("ix_payment_sessions_status", table_name="payment_sessions")
    op.drop_table("payment_sessions")

    op.drop_index("ix_batches_course_status", table_name="batches")
    op.drop_index("ix_batches_status", table_name="batches")
    op.drop_index("ix_batches_course_id", table_name="batches")
    op.drop_table("batches")

    op.drop_index("ix_courses_status", table_name="courses")
    op.drop_table("courses")

    op.drop_index("ux_admin_users_email_lower", table_name="admin_users")
    op.drop_table("admin_users")
