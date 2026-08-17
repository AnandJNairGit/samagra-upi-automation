# Phase 9 — Google Pay / UPI Bank Statement Import Implementation Plan

## 1. Overview & Primary Objective

Phase 9 implements an administrator-controlled statement import system designed to ingest, parse, normalize, and store bank transactions from Google Pay or bank statement export files.

### Core Architectural Guarantees:
- **Multi-Format Support**: Handles `.csv` text files and multi-sheet `.xlsx` Microsoft Excel workbooks using `openpyxl`.
- **Position-Based Mapping**: Uses 0-based column indices (`column_index`) rather than rigid header names, accommodating non-standard bank statement layouts.
- **Two-Step Workflow**: 
  - **Step 1 Preview**: 0 database writes; returns sheets, detected headers, and data preview with a 30-minute preview token.
  - **Step 2 Confirmation**: Validates mapping, verifies exact-file idempotency, filters duplicates, skips null reference rows, and persists normalized transactions.
- **File-Independent Deduplication**: Computes content fingerprint hashes (`source_transaction_key`) using normalized transaction data fields so duplicate rows across overlapping monthly statement files are identified and skipped.
- **Null Reference Filtering**: Statement rows missing a valid payment reference code are excluded from persistence and logged under `rows_without_reference`.
- **Import Deletion**: Admin endpoint and UI modal to delete statement imports and cascade deletion to associated bank transactions.
- **Strict Phase Boundary**: Zero automated reconciliation or state mutations to Phase 6 `payment_sessions` or Phase 7 `payment_submissions` (reserved for Phase 10).

---

## 2. Database Schema Design

### A. Table: `statement_imports`
Tracks metadata, column mapping configuration, and execution statistics for each imported statement file.

```sql
CREATE TABLE statement_imports (
    id BIGSERIAL PRIMARY KEY,
    public_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(20) NOT NULL, -- 'csv', 'xlsx'
    file_size BIGINT NOT NULL,
    file_checksum_sha256 VARCHAR(64) NOT NULL,
    canonical_mapping_hash VARCHAR(64) NOT NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'GOOGLE_PAY',
    selected_sheet_name VARCHAR(100) NULL,
    header_row_index INT NOT NULL DEFAULT 1,
    column_mapping JSONB NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'COMPLETED', -- 'COMPLETED', 'COMPLETED_WITH_ERRORS', 'FAILED'
    total_rows INT NOT NULL DEFAULT 0,
    valid_rows INT NOT NULL DEFAULT 0,
    invalid_rows INT NOT NULL DEFAULT 0,
    duplicate_rows INT NOT NULL DEFAULT 0,
    new_transactions INT NOT NULL DEFAULT 0,
    rows_without_reference INT NOT NULL DEFAULT 0,
    error_summary JSONB NULL,
    imported_by BIGINT NOT NULL REFERENCES admin_users(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ NULL
);

CREATE INDEX idx_statement_imports_canonical_hash ON statement_imports(canonical_mapping_hash);
CREATE INDEX idx_statement_imports_public_id ON statement_imports(public_id);
```

### B. Table: `bank_transactions`
Stores normalized individual transaction rows extracted from bank statements.

```sql
CREATE TABLE bank_transactions (
    id BIGSERIAL PRIMARY KEY,
    public_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    statement_import_id BIGINT NOT NULL REFERENCES statement_imports(id) ON DELETE RESTRICT,
    transaction_at TIMESTAMPTZ NULL,
    amount_inr BIGINT NULL, -- Amount stored in whole rupees (INTEGER)
    direction VARCHAR(10) NULL, -- 'CREDIT', 'DEBIT'
    reference_id VARCHAR(100) NULL, -- Primary payment reference code
    utr VARCHAR(100) NULL, -- 12-digit UTR number
    counterparty_name VARCHAR(250) NULL,
    description TEXT NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'GOOGLE_PAY',
    source_transaction_key VARCHAR(64) NULL, -- Content fingerprint hash for deduplication
    raw_row_data JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_bank_txns_import_id ON bank_transactions(statement_import_id);
CREATE INDEX idx_bank_txns_source_key ON bank_transactions(source, source_transaction_key);
CREATE INDEX idx_bank_txns_reference_id ON bank_transactions(reference_id);
CREATE INDEX idx_bank_txns_utr ON bank_transactions(utr);
```

---

## 3. Deduplication Architecture & Algorithms

### A. Exact-File Idempotency Key (`canonical_mapping_hash`)
Prevents importing the exact same file with identical sheet and column mapping twice:

$$\text{canonical\_raw} = \text{file\_checksum} + \text{"|"} + \text{sheet\_name} + \text{"|"} + \text{header\_row\_index} + \text{"|"} + \text{JSON}(\text{column\_mapping})$$

$$\text{canonical\_mapping\_hash} = \text{SHA256}(\text{canonical\_raw})$$

If a matching `COMPLETED` record exists in `statement_imports`, confirmation immediately returns `already_imported = true` without duplicating records.

### B. Transaction Content Fingerprint (`source_transaction_key`)
Prevents inserting duplicate transactions across overlapping monthly statements (e.g. August statement vs. August-September statement):

$$\text{fingerprint\_raw} = \text{source} + \text{"|"} + \text{reference\_id} + \text{"|"} + \text{utr} + \text{"|"} + \text{amount\_inr} + \text{"|"} + \text{direction} + \text{"|"} + \text{ISO8601}(\text{transaction\_at}) + \text{"|"} + \text{counterparty\_name} + \text{"|"} + \text{description}$$

$$\text{source\_transaction_key} = \text{SHA256}(\text{fingerprint\_raw})$$

Before inserting candidate rows, the service queries existing keys in chunks of 500. Matches are counted under `duplicate_rows` and skipped.

---

## 4. REST API Endpoint Specifications

| HTTP Method | Path | Description | Access |
| :--- | :--- | :--- | :--- |
| `POST` | `/v1/admin/statement-imports/preview` | Upload statement file (.csv/.xlsx), detect sheets & headers, receive preview token. | Admin JWT |
| `POST` | `/v1/admin/statement-imports/confirm` | Confirm column mapping, validate rows, deduplicate, filter null reference rows, and persist transactions. | Admin JWT |
| `GET` | `/v1/admin/statement-imports` | Fetch paginated history of past statement imports. | Admin JWT |
| `GET` | `/v1/admin/statement-imports/{public_id}` | Fetch audit detail card and summary metrics for an import. | Admin JWT |
| `GET` | `/v1/admin/statement-imports/{public_id}/transactions` | Fetch paginated normalized bank transaction records for an import. | Admin JWT |
| `DELETE` | `/v1/admin/statement-imports/{public_id}` | Delete a statement import record and cascade delete associated bank transactions. | Admin JWT |

---

## 5. Frontend User Interface Architecture

The admin interface (`/upi/admin/statement-imports`) features a 5-step wizard and accountant-friendly UI:

1. **Step 1: Upload File**: File picker supporting `.csv` and `.xlsx` files with drag & drop.
2. **Step 2: Select Sheet (Excel)**: Sheet dropdown selector for multi-sheet Excel workbooks.
3. **Step 3: Header Row Selection**: Configurable 1-indexed header row.
4. **Step 4: Column Mapping**: Dropdown mapping for 0-based column indices:
   - **Payment Reference Code** *(Required)*
   - **Credit Amount (₹)** *(Required)*
   - **Transaction Date** *(Optional)*
   - **Type / Direction** *(Optional)*
   - **Bank UTR Number** *(Optional)*
   - **Payer Name** *(Optional)*
   - **Description / Remarks** *(Optional)*
5. **Step 5: Preview & Confirmation**: Table preview of candidate rows before finalizing import.
6. **Audit History & Deletion**: Paginated audit table with plain-English summary cards (`TOTAL ENTRIES`, `NEW TRANSACTIONS`, `SKIPPED (DUPES)`, `VALID ENTRIES`, `MISSING REF CODE`) and red **Delete** action buttons with modal confirmation dialogs. Technical hashes (SHA256) are tucked inside a collapsible `<details>` panel (`⚙ Technical System Information (for IT Support)`).

---

## 6. Verification & Automated Test Coverage

- **Backend Unit & Integration Tests**: 159 passing tests (`pytest`).
  - `test_preview_csv_endpoint`: CSV preview and header parsing.
  - `test_preview_xlsx_multi_sheet_endpoint`: Multi-sheet Excel workbook sheet selection.
  - `test_confirm_import_csv_workflow`: 2-step preview->confirm workflow and single-use token invalidation.
  - `test_exact_duplicate_import_idempotency`: Idempotent handling of duplicate statement file uploads.
  - `test_delete_statement_import_endpoint`: End-to-end statement import deletion and cascading database cleanup.
  - `test_statement_parser`: Amount parsing, reference normalization, and fingerprint calculation.
- **Frontend Build**: Clean compilation via `npm --prefix frontend run build` (0 TypeScript/Vite errors).
