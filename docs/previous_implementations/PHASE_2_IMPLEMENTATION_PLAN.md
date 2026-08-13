# Phase 2 Implementation Plan & Execution Summary

**Phase**: 2 — PostgreSQL Database Foundation & Migrations  
**Status**: Completed & Verified  
**Date**: August 2026  
**Target Platform**: PostgreSQL 16 Alpine with SQLAlchemy 2.x and Alembic.

---

## 1. Architectural Mandate & Implemented Tables

Implemented the five core business tables for the UPI payment automation system:
1. `admin_users`
2. `courses`
3. `batches`
4. `payment_sessions`
5. `payment_submissions`

### Key Constraints & Decisions
1. **Whole-Rupee Monetary Representation**: `BIGINT amount_inr` with `CHECK (amount_inr > 0)`. No `amount_paise`, `FLOAT`, `DOUBLE`, or `DECIMAL`.
2. **Identifier Strategy**: `id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY` internally; `public_id UUID NOT NULL UNIQUE` externally.
3. **Historical Snapshots**: `payment_sessions` maintains immutable snapshot columns (`course_name_snapshot`, `batch_name_snapshot`, `amount_inr`, `upi_id_snapshot`, `payee_name_snapshot`, `upi_uri`).
4. **Current Submission & UTR Uniqueness**:
   - `CREATE UNIQUE INDEX ux_payment_submissions_current ON payment_submissions (payment_session_id) WHERE is_current = TRUE;`
   - `CREATE UNIQUE INDEX ux_payment_submissions_utr ON payment_submissions (utr);`
5. **Admin Deletion**: Deactivation only (`is_active = FALSE`), protected by `ON DELETE RESTRICT`.
6. **Concurrency & Locking Protection**:
   - `PaymentSubmissionService.submit_utr`: Acquires `SELECT ... FOR UPDATE` row lock on parent payment session.
   - `PaymentSubmissionService.approve_submission`: Acquires `SELECT ... FOR UPDATE` row locks on both submission and parent session, validating state and atomically synchronizing statuses.
   - `PaymentSubmissionService.reject_submission`: Acquires `SELECT ... FOR UPDATE` row locks on both submission and parent session, validating state and atomically recording rejection reason and synchronizing statuses.
7. **Clean Separation of Concerns**:
   - `app/models/`: SQLAlchemy 2.x declarative entity definitions.
   - `app/repositories/`: Pure persistence operations (CRUD, queries, row-locking queries).
   - `app/services/`: Business workflows, state synchronization, locking, and error translation.
   - `app/schemas/`: Pydantic input/output schemas with string sanitization.

---

## 2. Verification & Testing Matrix (29 Tests)

- **Unit Tests**: Entity definitions, defaults, relationships.
- **Constraint Tests**: Case-insensitive email, positive amount, date range check, status check constraints, foreign key restrictions, partial unique indexes.
- **Snapshot Immutability Tests**: Verified historical payment snapshots remain unmodified after course/batch alterations.
- **Repository Tests**: Pure persistence CRUD methods.
- **Service & Workflow Tests**:
  - Initial UTR submission workflow (`PENDING` $\rightarrow$ `SUBMITTED`).
  - Resubmission workflow after rejection (`REJECTED` $\rightarrow$ `SUBMITTED` with new current submission).
  - Dedicated approval workflow (`SUBMITTED` $\rightarrow$ `APPROVED` with reviewer tracking and timestamp).
  - Dedicated rejection workflow (`SUBMITTED` $\rightarrow$ `REJECTED` with reason recording and reviewer tracking).
  - State guard test verifying already processed submissions reject subsequent approve/reject attempts.
  - Domain error translation (`DuplicateUTRError`).
- **Live Concurrency Tests**:
  - `test_concurrent_utr_submissions_row_locking`: Concurrent UTR submissions serialized via row locking.
  - `test_concurrent_approval_rejection_row_locking`: Concurrent competing approve and reject requests serialized via row locking, guaranteeing exactly one valid transition and raising `InvalidSessionStateError` for the competing action.
- **Alembic Migrations**: Verified clean `alembic upgrade head` $\rightarrow$ `alembic downgrade base` $\rightarrow$ `alembic upgrade head`.
