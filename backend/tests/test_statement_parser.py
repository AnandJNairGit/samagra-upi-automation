"""Unit test suite for StatementParserService."""

import os
import pytest
from datetime import datetime, timezone
from app.services.statement_parser_service import StatementParserService
from app.schemas.statement_import import StatementColumnMapping, ColumnFieldMapping

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
CSV_PATH = os.path.join(FIXTURES_DIR, "sample_statement.csv")
XLSX_PATH = os.path.join(FIXTURES_DIR, "sample_statement.xlsx")


def test_validate_file_meta():
    parser = StatementParserService()
    assert parser.validate_file_meta("test.csv", 100) == "csv"
    assert parser.validate_file_meta("test.XLSX", 100) == "xlsx"

    with pytest.raises(ValueError, match="Unsupported file format"):
        parser.validate_file_meta("test.xlsm", 100)

    with pytest.raises(ValueError, match="Unsupported file format"):
        parser.validate_file_meta("test.pdf", 100)


def test_inspect_csv_headers_and_preview():
    parser = StatementParserService()
    with open(CSV_PATH, "rb") as f:
        file_bytes = f.read()

    file_type, sheets, selected_sheet, headers, preview_rows, total_rows = parser.inspect_file(
        file_bytes=file_bytes, filename="sample.csv", header_row_index=1
    )

    assert file_type == "csv"
    assert sheets == []
    assert selected_sheet is None
    assert len(headers) == 7
    assert headers[0].header == "Transaction Date"
    assert headers[2].header == "Transaction Remarks"
    assert total_rows == 4
    assert len(preview_rows) == 4


def test_inspect_xlsx_multi_sheet():
    parser = StatementParserService()
    with open(XLSX_PATH, "rb") as f:
        file_bytes = f.read()

    # Inspect without sheet name -> defaults to first sheet 'Summary'
    file_type, sheets, selected_sheet, headers, preview_rows, total_rows = parser.inspect_file(
        file_bytes=file_bytes, filename="sample.xlsx", header_row_index=1
    )

    assert file_type == "xlsx"
    assert sheets == ["Summary", "Transactions", "Account Details"]
    assert selected_sheet == "Summary"

    # Now inspect with explicit sheet_name = 'Transactions' and header_row_index = 2
    _, _, selected_sheet_2, headers_2, preview_rows_2, total_rows_2 = parser.inspect_file(
        file_bytes=file_bytes, filename="sample.xlsx", sheet_name="Transactions", header_row_index=2
    )

    assert selected_sheet_2 == "Transactions"
    assert len(headers_2) == 7
    assert headers_2[2].header == "Transaction Remarks"
    assert total_rows_2 == 4
    assert len(preview_rows_2) == 4


def test_amount_parsing_whole_rupees():
    parser = StatementParserService()
    assert parser.parse_amount("₹4,000") == 4000
    assert parser.parse_amount("Rs 4000.00") == 4000
    assert parser.parse_amount("2500") == 2500

    # Fractional paisa should be rejected
    with pytest.raises(ValueError, match="fractional paisa"):
        parser.parse_amount("4000.50")


def test_reference_code_preservation():
    parser = StatementParserService()
    raw = " ADITYA_3210_YON2 "
    normalized = parser.normalize_reference_id(raw)
    assert normalized == "ADITYA_3210_YON2"
    assert normalized.isupper()
    assert "_" in normalized


def test_position_based_column_mapping():
    """Verify position-based indexing resolves correctly even when duplicate headers exist."""
    parser = StatementParserService()
    row = ["2026-08-16 10:30:00", "CREDIT", "ADITYA_3210_YON2", "2500", "987654321098"]
    mapping = StatementColumnMapping(
        reference_id=ColumnFieldMapping(column_index=2, header="Transaction Remarks"),
        amount=ColumnFieldMapping(column_index=3, header="Amount"),
    )

    ref_val = row[mapping.reference_id.column_index]
    amt_val = row[mapping.amount.column_index]

    assert parser.normalize_reference_id(ref_val) == "ADITYA_3210_YON2"
    assert parser.parse_amount(amt_val) == 2500


def test_file_independent_source_transaction_key_fingerprint():
    """Verify source_transaction_key fallback does not depend on file location or row number."""
    parser = StatementParserService()

    dt = datetime(2026, 8, 16, 10, 30, tzinfo=timezone.utc)

    # Key 1 from File A
    key_file_a = parser.compute_source_transaction_key(
        source="GOOGLE_PAY",
        reference_id="ADITYA_3210_YON2",
        utr=None,
        amount_inr=2500,
        direction="CREDIT",
        transaction_at=dt,
        counterparty="Aditya Nair",
        description="UPI Fee",
    )

    # Key 2 from File B (overlapping statement, different row)
    key_file_b = parser.compute_source_transaction_key(
        source="GOOGLE_PAY",
        reference_id="ADITYA_3210_YON2",
        utr=None,
        amount_inr=2500,
        direction="CREDIT",
        transaction_at=dt,
        counterparty="Aditya Nair",
        description="UPI Fee",
    )

    # Must be identical for clean deduplication across overlapping files!
    assert key_file_a == key_file_b
    assert key_file_a == "GOOGLE_PAY_REF_ADITYA_3210_YON2"
