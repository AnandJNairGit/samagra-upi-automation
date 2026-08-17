"""Statement import database model for tracking uploaded bank statement files and column mapping metadata."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, IdentityIdMixin, PublicIdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.admin_user import AdminUser
    from app.models.bank_transaction import BankTransaction


class StatementImport(Base, IdentityIdMixin, PublicIdMixin, TimestampMixin):
    """Statement import record representing an uploaded CSV or Excel bank statement."""

    __tablename__ = "statement_imports"

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)  # csv, xlsx
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    canonical_mapping_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    source: Mapped[str] = mapped_column(String(50), default="GOOGLE_PAY", nullable=False)
    selected_sheet_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    header_row_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    column_mapping: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="COMPLETED", nullable=False)  # COMPLETED, COMPLETED_WITH_ERRORS, FAILED

    total_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invalid_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_transactions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rows_without_reference: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    error_summary: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    imported_by: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("admin_users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    admin_user: Mapped["AdminUser"] = relationship(
        "AdminUser",
    )
    bank_transactions: Mapped[List["BankTransaction"]] = relationship(
        "BankTransaction",
        back_populates="statement_import",
        cascade="none",
    )

    __table_args__ = (
        CheckConstraint("file_size >= 0", name="ck_statement_imports_file_size"),
        CheckConstraint("status IN ('COMPLETED', 'COMPLETED_WITH_ERRORS', 'FAILED')", name="ck_statement_imports_status"),
        Index("ix_statement_imports_checksum", "file_checksum_sha256"),
        Index("ix_statement_imports_canonical_hash", "canonical_mapping_hash"),
        Index("ix_statement_imports_created_at", "created_at"),
        Index("ix_statement_imports_imported_by", "imported_by"),
    )
