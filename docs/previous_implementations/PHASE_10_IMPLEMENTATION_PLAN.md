# Phase 10: Reconciliation Engine — Implementation Plan & Summary

## Overview

Phase 10 implements the deterministic payment reconciliation engine that matches imported bank statement transactions against registered participant payment sessions. Reconciliation is triggered by the admin via a single **Match** button in the Admin Batch Workspace.

---

## Features Implemented

### 1. Reconciliation Engine (`ReconciliationService`)

**File**: `backend/app/services/reconciliation_service.py`

A deterministic, batch-scoped matching algorithm that:

- Accepts a `batch_public_id` and `statement_import_public_id`
- Fetches all `BankTransaction` records from the selected import
- Bulk-fetches all `PaymentSession` records for the batch indexed by `reference_id`
- For each bank transaction, classifies it into one of 7 result statuses:

| Status | Condition |
| :--- | :--- |
| `MATCHED` | Reference code found + amount matches. Session auto-approved. |
| `AMOUNT_MISMATCH` | Reference found but amount differs. |
| `UTR_MISMATCH` | Reference + amount match, but both UTRs differ. |
| `UNKNOWN_REFERENCE` | Reference not found in batch sessions. |
| `NO_REFERENCE` | Bank transaction has no reference code. |
| `DUPLICATE_TRANSACTION` | Same reference appears multiple times in statement. |
| `UNMATCHED` | DEBIT / non-credit transaction. |

**Batch-isolation invariant**: All PaymentSession lookups are filtered to `batch_id` at SQL level.

**Direction=NULL fallback**: When `direction` is NULL (not mapped during import), the engine treats the transaction as CREDIT.

**Auto-approve on match**: When a transaction is classified as `MATCHED`:
- `PaymentSession.status` is set to `"APPROVED"`
- `PaymentSubmission.status` is set to `"APPROVED"` (if submission exists)

**No history retention**: Each Match click for a batch deletes the previous run and creates a fresh one.

---

### 2. Match Button & Statement Dropdown (Frontend)

**File**: `frontend/src/pages/AdminBatchWorkspacePage.tsx`

- A statement selector `<select>` appears in the Public Registrations & Payments table header.
- A **Match** button triggers `POST /v1/admin/reconciliation/run`.
- Table data refreshes automatically on completion.

---

### 3. Matched Status Badges in Table

- Rows with status `APPROVED` display a green **Matched** pill badge in the Status column.

---

### 4. UTR Made Optional (Phase 7 Patch)

**Files changed**:
- `backend/app/models/payment_submission.py` — utr nullable=True, unique index removed
- `backend/app/schemas/payment_submission.py` — utr: Optional[str] = None
- `backend/app/services/payment_submission_service.py` — validates UTR only if non-null
- `backend/app/services/whatsapp_service.py` — mask_utr() handles None
- `frontend/src/pages/PublicPaymentPage.tsx` — UTR field is optional
- `frontend/src/services/publicApi.ts` — utr: string | null

**DB Migration applied**:
`
DROP INDEX IF EXISTS ux_payment_submissions_utr;
ALTER TABLE payment_submissions ALTER COLUMN utr DROP NOT NULL;
CREATE INDEX IF NOT EXISTS ix_payment_submissions_utr ON payment_submissions(utr);
`

---

### 5. Test Data Tooling (Root Directory)

| Script | Description |
| :--- | :--- |
| `seed_manual_test_data.py` | Creates 3 courses, 3 batches, 6 sessions. Generates demo_test_statement.csv. |
| `clean_manual_test_data.py` | Removes only test-seeded records. |
| `clear_db.py` | Truncates all business tables. Preserves admin accounts. |

### Generated CSV Column Mapping

| Col | Header | Map To |
| :--- | :--- | :--- |
| 0 | Date | Transaction Date |
| 1 | Description | Description |
| 2 | Ref No | Reference ID (Required) |
| 3 | Direction | Direction CREDIT/DEBIT |
| 4 | Amount | Amount (Required) |
| 5 | UTR | UTR (optional) |

---

## Database Tables

- `reconciliation_runs` — one run per match click, stores aggregate counts
- `reconciliation_results` — one row per bank transaction, stores classification + match flags
- `payment_sessions` — status updated to APPROVED on MATCHED
- `payment_submissions` — utr now nullable; status updated to APPROVED on MATCHED

## API Endpoints

| Method | Path | Purpose |
| :--- | :--- | :--- |
| POST | /v1/admin/reconciliation/run | Trigger reconciliation |
| GET | /v1/admin/reconciliation/runs | List runs |
| GET | /v1/admin/reconciliation/runs/{id} | Get run summary |
| GET | /v1/admin/reconciliation/runs/{id}/results | Get paginated results |
| GET | /v1/admin/reconciliation/results/{id} | Get single result |
