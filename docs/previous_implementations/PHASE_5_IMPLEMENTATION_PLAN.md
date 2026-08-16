# Phase 5 Implementation Plan & Execution Summary

**Phase**: 5 — Public Registration  
**Status**: Completed & Verified  
**Date**: August 2026  
**Target Platform**: FastAPI (Python 3.12), PostgreSQL 16 Alpine with SQLAlchemy 2.x (asyncpg), React 18 + TypeScript + Vite.

---

## 1. Primary Objectives & Business Invariants

Phase 5 implements the public participant registration flow for cohorts configured by administrators, without allowing participants to choose or alter courses, batches, or fees.

### Core Business Rules & Invariants
1. **Public Registration Link Context**:
   - The public registration link is batch-scoped: `/upi/register/<batch_public_id>`.
   - The batch public UUID is the authoritative public identifier. No course selector, batch selector, or fee input exists on the public registration page.
2. **Zero Database Migrations**:
   - Uses the existing `batches.public_id` column without adding new tables (`participants`, `registrations`, `public_links`) or schema changes.
3. **Public Batch Availability Rule**:
   - `GET /v1/public/batches/{batch_public_id}` only exposes a cohort if:
     $$\text{batch.status} == \text{'ACTIVE'} \quad \text{AND} \quad \text{course.status} == \text{'ACTIVE'}$$
   - Any inactive, archived, or non-existent batch/course returns a generic `404 Not Found` with message `"This registration link is no longer available."`.
4. **Minimal Public Information Disclosure**:
   - Public batch responses omit internal database IDs, admin metadata, payment status, and database internals.
5. **Strict Phase 5 / Phase 6 Boundary**:
   - Phase 5 terminates at validated participant registration context (`PublicRegistrationValidateResponse`).
   - Does **NOT** create a `payment_sessions` record, generate UPI references/URIs, create QR codes, or simulate payment flows.
6. **Server-Side Authoritative Derivation & Tamper Resistance**:
   - The validation endpoint (`POST /v1/public/register/validate`) derives the course name, batch name, and amount strictly from the database. Client attempts to supply `amount_inr` or extra fields are strictly forbidden (`extra="forbid"` $\rightarrow$ `422 Unprocessable Entity`).

---

## 2. Implemented API Endpoints

All Phase 5 endpoints are public and unauthenticated (do **not** require `require_admin`).

| Method | Endpoint | Rate Limit | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/v1/public/batches/{batch_public_id}` | 60 req/min per IP | Resolves public course title, batch name, fee in INR, and start/end dates for active cohorts. |
| `POST` | `/v1/public/register/validate` | 20 req/min per (IP + batch_id) | Validates participant contact details (Name, Indian phone, Email) against active cohort state. |

---

## 3. Implemented File Inventory

### Backend Components
* `backend/app/schemas/public.py`:
  - `PublicBatchResponse`: minimal public cohort schema (`public_id`, `course_name`, `batch_name`, `amount_inr`, `starts_at`, `ends_at`).
  - `PublicRegistrationValidateRequest`: participant registration payload (`batch_public_id`, `full_name`, `phone`, `email`) with Indian mobile regex validation (`^[6-9]\d{9}$`) and whitespace trimming.
  - `PublicRegistrationValidateResponse`: authoritative validated context for Phase 6 handoff.
* `backend/app/services/public_registration_service.py`:
  - `get_active_batch_by_public_id(db, batch_public_id)`: enforces active batch & active course rule.
  - `validate_registration_context(db, payload)`: validates participant data against active cohort.
* `backend/app/services/exceptions.py`:
  - Added `PublicBatchUnavailableError` and `ParticipantValidationError`.
* `backend/app/api/v1/public.py`:
  - Public FastAPI router mounted under `/public`.
* `backend/tests/test_public_registration_api.py`:
  - 15 automated integration tests for public endpoints.

### Frontend Components
* `frontend/src/types/public.ts`:
  - TypeScript types: `PublicBatch`, `ParticipantFormData`, `PublicRegistrationContext`, `FormErrors`.
* `frontend/src/services/publicApi.ts`:
  - Public HTTP client for `fetchPublicBatch` and `validateRegistration`.
* `frontend/src/pages/PublicRegistrationPage.tsx`:
  - Mobile-first public enrollment page (`/upi/register/:batchPublicId`) with read-only program summary, participant form, error states, and Phase 6 handoff boundary.
* `frontend/src/pages/AdminBatchesPage.tsx`:
  - Added "Copy Link" action button to active batch rows with clipboard integration and visual feedback.
* `frontend/src/app/App.tsx`:
  - Mounted public registration route `/upi/register/:batchPublicId` (and `/register/:batchPublicId`).

---

## 4. Verification & Testing Matrix (99 Tests)

Executed via Docker against PostgreSQL 16:

```bash
docker compose run --rm backend pytest tests/ -v
======================= 99 passed in 11.84s ========================
```

### Test Breakdown
* **Public Registration API Suite** (`tests/test_public_registration_api.py`): **15/15 PASSED**
  - Active batch lookup returns 200 with minimal payload.
  - Inactive batch returns 404 with generic message.
  - Archived batch returns 404 with generic message.
  - Active batch under inactive course returns 404.
  - Active batch under archived course returns 404.
  - Nonexistent public batch returns 404.
  - Public response omits internal database IDs.
  - Public endpoint accessible without admin auth.
  - Admin endpoints remain strictly protected (401).
  - Validation endpoint returns authoritative context.
  - Validation does **not** insert `PaymentSession` records in the database.
  - Client amount tampering is rejected (`extra="forbid"` $\rightarrow$ 422).
  - Invalid Indian phone numbers rejected with 422.
  - Invalid emails rejected with 422.
  - Rate limiter blocks requests exceeding sliding-window quota (429).
* **Phases 1–4 Regression Suites**: **84/84 PASSED**
  - Course & Batch Management, Argon2id auth, JWT claims, models, constraints, and historical snapshot immutability.

### Frontend Compilation & Live Browser Verification
* **TypeScript & Vite Build**: `tsc -b && vite build` compiled in 1.29s with 0 errors.
* **End-to-End Browser Session**:
  - Admin copied public link from Batches console (`/upi/admin/batches`).
  - Navigated to `/upi/register/<batch_public_id>` $\rightarrow$ verified read-only program context and participant form.
  - Submitted participant data $\rightarrow$ verified validated registration confirmation.
  - Deactivated batch $\rightarrow$ verified public link transitioned to "Registration Unavailable".
