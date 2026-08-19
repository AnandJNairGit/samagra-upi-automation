# Database Architecture & Schema Specification (Phases 1 – 10)

Comprehensive technical documentation for the **Samagra UPI Automation** PostgreSQL 16 database foundation.

---

## 1. Entity-Relationship Architecture

```mermaid
erDiagram
    ADMIN_USERS ||--o{ ADMIN_SESSIONS : "authenticates"
    ADMIN_USERS ||--o{ PAYMENT_SUBMISSIONS : "reviews"
    ADMIN_USERS ||--o{ STATEMENT_IMPORTS : "uploads"
    ADMIN_USERS ||--o{ RECONCILIATION_RUNS : "initiates"
    COURSES ||--o{ BATCHES : "contains"
    COURSES ||--o{ PAYMENT_SESSIONS : "historical reference"
    BATCHES ||--o{ PAYMENT_SESSIONS : "generates"
    BATCHES ||--o{ RECONCILIATION_RUNS : "reconciled against"
    PAYMENT_SESSIONS ||--o{ PAYMENT_SUBMISSIONS : "receives attempts"
    PAYMENT_SESSIONS ||--o{ RECONCILIATION_RESULTS : "classified by"
    STATEMENT_IMPORTS ||--o{ BANK_TRANSACTIONS : "contains"
    STATEMENT_IMPORTS ||--o{ RECONCILIATION_RUNS : "used in"
    RECONCILIATION_RUNS ||--o{ RECONCILIATION_RESULTS : "produces"
    BANK_TRANSACTIONS ||--o{ RECONCILIATION_RESULTS : "classified as"

    ADMIN_USERS {
        bigint id PK
        uuid public_id UK
        varchar email UK "LOWER(email) functional index"
        text password_hash "Argon2id"
        varchar full_name
        boolean is_active "Deactivation only"
        timestamptz last_login_at
        timestamptz created_at
        timestamptz updated_at
    }

    ADMIN_SESSIONS {
        bigint id PK
        uuid public_id UK
        bigint admin_user_id FK "ON DELETE RESTRICT"
        varchar refresh_token_hash UK "SHA-256 digest of secret"
        text user_agent
        inet ip_address "PostgreSQL INET"
        timestamptz expires_at "Index ix_admin_sessions_expires_at"
        timestamptz revoked_at "Compound index (admin_user_id, revoked_at)"
        timestamptz created_at
        timestamptz last_used_at
    }

    COURSES {
        bigint id PK
        uuid public_id UK
        varchar name
        text description
        varchar status "ACTIVE, INACTIVE, ARCHIVED"
        timestamptz created_at
        timestamptz updated_at
    }

    BATCHES {
        bigint id PK
        uuid public_id UK
        bigint course_id FK "ON DELETE RESTRICT"
        varchar name
        bigint amount_inr "CHECK > 0 (Whole Rupees)"
        varchar status "ACTIVE, INACTIVE, ARCHIVED"
        timestamptz starts_at
        timestamptz ends_at "CHECK >= starts_at"
        timestamptz created_at
        timestamptz updated_at
    }

    PAYMENT_SESSIONS {
        bigint id PK
        uuid public_id UK
        varchar full_name
        varchar phone
        varchar email
        bigint course_id FK "ON DELETE RESTRICT"
        bigint batch_id FK "ON DELETE RESTRICT"
        varchar course_name_snapshot "Immutable snapshot"
        varchar batch_name_snapshot "Immutable snapshot"
        bigint amount_inr "CHECK > 0 (Immutable snapshot)"
        varchar reference_id UK "Unique UPI Reference"
        varchar upi_id_snapshot "Immutable snapshot"
        varchar payee_name_snapshot "Immutable snapshot"
        text upi_uri "Immutable snapshot"
        varchar status "PENDING, SUBMITTED, REVIEW_REQUIRED, APPROVED, REJECTED, EXPIRED"
        timestamptz expires_at
        timestamptz created_at
        timestamptz updated_at
    }

    PAYMENT_SUBMISSIONS {
        bigint id PK
        uuid public_id UK
        bigint payment_session_id FK "ON DELETE RESTRICT"
        varchar utr "Optional — NULL if not submitted by participant"
        varchar status "SUBMITTED, REVIEW_REQUIRED, APPROVED, REJECTED"
        timestamptz submitted_at
        bigint reviewed_by FK "ON DELETE RESTRICT"
        timestamptz reviewed_at
        text rejection_reason
        boolean is_current "Partial unique WHERE is_current=TRUE"
        timestamptz created_at
        timestamptz updated_at
    }

    STATEMENT_IMPORTS {
        bigint id PK
        uuid public_id UK
        varchar filename
        varchar file_type "csv, xlsx"
        bigint file_size
        varchar file_checksum_sha256
        varchar canonical_mapping_hash
        varchar source "GOOGLE_PAY"
        varchar selected_sheet_name
        int header_row_index
        jsonb column_mapping
        varchar status "COMPLETED, COMPLETED_WITH_ERRORS, FAILED"
        int total_rows
        int valid_rows
        int invalid_rows
        int duplicate_rows
        int new_transactions
        int rows_without_reference
        jsonb error_summary
        bigint imported_by FK "ON DELETE RESTRICT"
        timestamptz created_at
        timestamptz completed_at
    }

    BANK_TRANSACTIONS {
        bigint id PK
        uuid public_id UK
        bigint statement_import_id FK "ON DELETE RESTRICT"
        timestamptz transaction_at
        bigint amount_inr "Whole rupees"
        varchar direction "CREDIT, DEBIT — NULL if not mapped during import"
        varchar reference_id "Primary payment reference"
        varchar utr "12-digit UTR"
        varchar counterparty_name
        text description
        varchar source "GOOGLE_PAY"
        varchar source_transaction_key "SHA-256 fingerprint hash"
        jsonb raw_row_data
        timestamptz created_at
    }

    RECONCILIATION_RUNS {
        bigint id PK
        uuid public_id UK
        bigint statement_import_id FK "ON DELETE RESTRICT"
        bigint batch_id FK "ON DELETE RESTRICT"
        bigint initiated_by FK "ON DELETE RESTRICT"
        varchar status "RUNNING, COMPLETED, FAILED"
        int total_transactions
        int credit_transactions
        int debit_transactions
        int matched_count
        int amount_mismatch_count
        int unknown_reference_count
        int no_reference_count
        int utr_mismatch_count
        int duplicate_transaction_count
        int needs_review_count
        int unmatched_count
        timestamptz started_at
        timestamptz completed_at
        timestamptz created_at
    }

    RECONCILIATION_RESULTS {
        bigint id PK
        uuid public_id UK
        bigint reconciliation_run_id FK "ON DELETE CASCADE"
        bigint bank_transaction_id FK "ON DELETE RESTRICT"
        bigint payment_session_id FK "ON DELETE RESTRICT, nullable"
        bigint payment_submission_id FK "ON DELETE RESTRICT, nullable"
        varchar status "MATCHED, AMOUNT_MISMATCH, UTR_MISMATCH, UNKNOWN_REFERENCE, NO_REFERENCE, DUPLICATE_TRANSACTION, UNMATCHED"
        boolean reference_match
        boolean amount_match
        boolean utr_match
        boolean payer_match
        varchar reason_code
        text explanation
        timestamptz created_at
    }
```

---

## 2. Core Architectural Decisions

### 2.1 Whole-Rupee Monetary Representation (`BIGINT amount_inr`)
- Course fees and payment amounts are strictly represented in **whole Indian Rupees (INR)**:
  - Example: `₹2000` is stored directly as `2000`.
- **Prohibitions**:
  - No `amount_paise` columns.
  - No `FLOAT`, `DOUBLE PRECISION`, or arbitrary decimal types.
- **Invariant**: All monetary columns enforce `CHECK (amount_inr > 0)`.

### 2.2 Primary Key & Identifier Strategy
- **Internal Relational IDs**: `id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY` on every table for compact joins and optimal B-tree index performance. Internal IDs are never exposed in public endpoints.
- **External Public IDs**: `public_id UUID NOT NULL UNIQUE` generated via Python `uuid.uuid4()`. All public/API interactions reference `public_id`.

### 2.3 Historical Snapshot Strategy
To maintain absolute historical financial auditability:
- When a `payment_sessions` record is generated, it copies immutable snapshots:
  - `course_name_snapshot`
  - `batch_name_snapshot`
  - `amount_inr`
  - `upi_id_snapshot`
  - `payee_name_snapshot`
  - `upi_uri`
- Future updates to course titles, cohort names, batch prices, or institutional UPI IDs will **never** alter historical payment session records.

### 2.4 Timestamp Strategy & `updated_at` Contract
- All timestamps use `TIMESTAMPTZ` (UTC).
- `created_at`: Database-defaulted with `server_default=func.now()`.
- `updated_at`: Database-initialized with `server_default=func.now()` and consistently maintained at the application layer by SQLAlchemy via `onupdate=func.now()`.
- Python code strictly uses timezone-aware datetimes (`datetime.timezone.utc`).

### 2.5 Admin Account Deletion Invariant
- Admin accounts are **deactivated (`is_active = FALSE`)**, never physically deleted.
- The `ON DELETE RESTRICT` constraint on `payment_submissions.reviewed_by` ensures audit trail integrity.

---

## 3. Status Lifecycle & Invariants

```text
[ Participant Checkout ]
          │
          ▼
       PENDING ──(Initial UTR Submitted)──► SUBMITTED
                                               │
                                               ▼
                                        REVIEW_REQUIRED
                                         │            │
                           (Admin Approve)            (Admin Reject)
                                         │            │
                                         ▼            ▼
                                     APPROVED     REJECTED
                                                      │
                                           (Corrected UTR Submitted)
                                                      │
                                                      ▼
                                                  SUBMITTED
```

| Payment Session Status | Invariant Condition for Submissions | Next Allowed Transitions |
| :--- | :--- | :--- |
| **`PENDING`** | No `PaymentSubmission` exists for this session. | $\rightarrow$ `SUBMITTED`, `EXPIRED` |
| **`SUBMITTED`** | Current `PaymentSubmission` (`is_current = TRUE`) exists with status `SUBMITTED` or `REVIEW_REQUIRED`. | $\rightarrow$ `REVIEW_REQUIRED`, `APPROVED`, `REJECTED` |
| **`REVIEW_REQUIRED`** | Current `PaymentSubmission` has status `REVIEW_REQUIRED`. | $\rightarrow$ `APPROVED`, `REJECTED` |
| **`APPROVED`** | Current `PaymentSubmission` has status `APPROVED` (terminal). | *(Terminal)* |
| **`REJECTED`** | Current `PaymentSubmission` has status `REJECTED`. | $\rightarrow$ `SUBMITTED` (on corrected UTR submission) |
| **`EXPIRED`** | Session timed out before valid submission (terminal). | *(Terminal)* |

---

## 4. Concurrency & Locking Strategy

- **UTR Submission Locking**: When updating or inserting a new UTR submission for a payment session, `PaymentSubmissionService.submit_utr` acquires an explicit row-level lock on the target `PaymentSession` (`SELECT ... FOR UPDATE` via `with_for_update()`):
  1. Lock target `PaymentSession` row (`SELECT ... FOR UPDATE`).
  2. Validate legal status (`PENDING` or `REJECTED`).
  3. Mark existing submission for the session `is_current = FALSE`.
  4. Insert new submission with `is_current = TRUE` and status `SUBMITTED`.
  5. Update `PaymentSession.status = 'SUBMITTED'`.
  6. Commit transaction.
- **Approval / Rejection Locking**: When an admin reviews a payment submission, `PaymentSubmissionService.approve_submission` and `PaymentSubmissionService.reject_submission` acquire explicit row locks on both the target submission and its parent session:
  1. Lock target `PaymentSubmission` row (`SELECT ... FOR UPDATE`).
  2. Validate submission status (`SUBMITTED` or `REVIEW_REQUIRED`).
  3. Lock parent `PaymentSession` row (`SELECT ... FOR UPDATE`).
  4. Validate session status (`SUBMITTED` or `REVIEW_REQUIRED`).
  5. Atomically update submission status (`APPROVED` / `REJECTED`), reviewer metadata, and session status.
  6. Commit transaction.
- **Partial Unique Index Protection**: `CREATE UNIQUE INDEX ux_payment_submissions_current ON payment_submissions (payment_session_id) WHERE is_current = TRUE;` guarantees at the database engine level that no two concurrent processes can leave multiple active submissions.

---

## 5. Indexing Catalog

| Table | Index Name | Columns / Expression | Type / Purpose |
| :--- | :--- | :--- | :--- |
| `admin_users` | `ux_admin_users_email_lower` | `LOWER(email)` | Functional Unique Index |
| `admin_sessions` | `ux_admin_sessions_public_id` | `public_id` | Unique UUID Index |
| `admin_sessions` | `ux_admin_sessions_refresh_token_hash` | `refresh_token_hash` | Unique Secret Hash Index |
| `admin_sessions` | `ix_admin_sessions_admin_user_revoked` | `admin_user_id, revoked_at` | Active Sessions Compound Index |
| `admin_sessions` | `ix_admin_sessions_expires_at` | `expires_at` | Session Expiry Cleanup Index |
| `courses` | `ix_courses_status` | `status` | Status Filtering |
| `batches` | `ix_batches_course_id` | `course_id` | Foreign Key Lookup |
| `batches` | `ix_batches_status` | `status` | Status Filtering |
| `batches` | `ix_batches_course_status` | `course_id, status` | Compound Query Support |
| `payment_sessions` | `ux_payment_sessions_reference_id`| `reference_id` | Unique Constraint Index |
| `payment_sessions` | `ix_payment_sessions_status` | `status` | Lifecycle Filtering |
| `payment_sessions` | `ix_payment_sessions_phone` | `phone` | Participant Lookup |
| `payment_sessions` | `ix_payment_sessions_created_at`| `created_at` | Time-series Ordering |
| `payment_sessions` | `ix_payment_sessions_batch_status`| `batch_id, status` | Cohort Payment Filtering |
| `payment_submissions`| `ix_payment_submissions_utr` | `utr` | Non-unique search index (UTR is now optional/nullable) |
| `payment_submissions`| `ux_payment_submissions_current` | `payment_session_id WHERE is_current = TRUE` | Partial Unique Index |
| `payment_submissions`| `ix_payment_submissions_payment_session`| `payment_session_id` | Foreign Key Lookup |
| `payment_submissions`| `ix_payment_submissions_status` | `status` | Lifecycle Filtering |
| `payment_submissions`| `ix_payment_submissions_submitted_at`| `submitted_at` | Audit Time Ordering |
| `statement_imports` | `ux_statement_imports_public_id` | `public_id` | Unique UUID Index |
| `statement_imports` | `ix_statement_imports_canonical_hash` | `canonical_mapping_hash` | Exact-File Idempotency Lookup Index |
| `bank_transactions` | `ux_bank_transactions_public_id` | `public_id` | Unique UUID Index |
| `bank_transactions` | `ix_bank_transactions_import_id` | `statement_import_id` | Foreign Key Audit Lookup |
| `bank_transactions` | `ix_bank_transactions_source_key` | `source, source_transaction_key` | Deduplication Fingerprint Index |
| `bank_transactions` | `ix_bank_transactions_reference_id` | `reference_id` | Reconciliation Primary Index |
| `bank_transactions` | `ix_bank_transactions_utr` | `utr` | Bank UTR Secondary Index |
| `reconciliation_runs` | `ux_reconciliation_runs_public_id` | `public_id` | Unique UUID Index |
| `reconciliation_runs` | `ix_reconciliation_runs_batch_id` | `batch_id` | Batch Lookup Index |
| `reconciliation_runs` | `ix_reconciliation_runs_statement_import_id` | `statement_import_id` | Statement Lookup Index |
| `reconciliation_results` | `ux_reconciliation_results_public_id` | `public_id` | Unique UUID Index |
| `reconciliation_results` | `ix_reconciliation_results_run_id` | `reconciliation_run_id` | Run Lookup Index |
| `reconciliation_results` | `ix_reconciliation_results_payment_session_id` | `payment_session_id` | Session Lookup Index |
| `reconciliation_results` | `ix_reconciliation_results_bank_transaction_id` | `bank_transaction_id` | Transaction Lookup Index |

---

## 6. Migration & Database Operations

### Run Migrations to Head
```bash
docker compose exec backend alembic upgrade head
```

### Rollback Migration
```bash
docker compose exec backend alembic downgrade base
```

### Inspect Database Schema
```bash
docker compose exec postgres psql -U app_user -d training_payments -c "\dt"
docker compose exec postgres psql -U app_user -d training_payments -c "\d+ payment_sessions"
docker compose exec postgres psql -U app_user -d training_payments -c "\d+ payment_submissions"
```

### Populate Development Seed Data
```bash
docker compose exec backend python scripts/seed_dev.py
```
