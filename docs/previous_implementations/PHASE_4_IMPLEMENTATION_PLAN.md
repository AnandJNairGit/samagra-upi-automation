# Phase 4 Implementation Plan & Execution Summary

**Phase**: 4 — Course & Batch Management  
**Status**: Completed & Verified  
**Date**: August 2026  
**Target Platform**: FastAPI (Python 3.12), PostgreSQL 16 Alpine with SQLAlchemy 2.x (asyncpg), React 18 + TypeScript + Vite.

---

## 1. Primary Objectives & Business Invariants

Phase 4 delivers administrative control over Courses and Batches (Cohorts), forming the catalog layer that feeds public registration and UPI payment sessions.

### Core Business Rules & Invariants
1. **Lifecycle State Machine**:
   - Both `Course` and `Batch` support three discrete states: `ACTIVE`, `INACTIVE`, and `ARCHIVED`.
   - Permitted state transitions:
     - `ACTIVE` $\leftrightarrow$ `INACTIVE`
     - `ACTIVE` $\rightarrow$ `ARCHIVED`
     - `INACTIVE` $\rightarrow$ `ARCHIVED`
   - `ARCHIVED` is strictly **terminal and read-only**:
     - Cannot transition to `ACTIVE` or `INACTIVE` (rejected with `400 Bad Request`).
     - Any mutative update to name, description, amount, or dates on an archived entity is rejected with `400 Bad Request`.
2. **Decoupled Course & Batch Lifecycles**:
   - Deactivating or archiving a parent Course does **not** cascade state mutations to child Batches.
   - Child batches retain their independent status (`ACTIVE`, `INACTIVE`, or `ARCHIVED`).
   - New Batches cannot be created under an `ARCHIVED` Course.
   - Batches can be created under an `INACTIVE` Course (useful for pre-launch cohort preparation).
3. **Course Reassignment Restrictions**:
   - A Batch can be reassigned to a different Course **only if zero payment sessions exist** for that batch.
   - If 1 or more `payment_sessions` reference the batch, attempts to change `course_public_id` are rejected with `409 Conflict`.
   - Reassigning a batch to an `ARCHIVED` course is rejected with `400 Bad Request`.
4. **Historical Snapshot Immutability**:
   - Historical snapshots in `payment_sessions` (`course_name_snapshot`, `batch_name_snapshot`, `amount_inr_snapshot`) remain permanently immutable even when parent course or batch names/fees are edited.
5. **Deterministic Concurrency & Row Locking**:
   - Mutations acquire isolated row locks via `SELECT ... FROM batches WHERE public_id = :id FOR UPDATE` before applying updates.
   - Avoids PostgreSQL syntax errors by strictly isolating `FOR UPDATE` from nullable outer-join queries.

---

## 2. Implemented API Endpoints

All endpoints require administrative authentication via `require_admin` (`Authorization: Bearer <access_token>`).

### Course Management Endpoints

| Method | Endpoint | Query Parameters | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/v1/admin/courses` | `status` (`ACTIVE`/`INACTIVE`/`ARCHIVED`) | Returns courses with dynamic `batch_count`, ordered deterministically by `created_at DESC, id DESC`. |
| `POST` | `/v1/admin/courses` | — | Creates a new course. Status defaults to `ACTIVE`. `ARCHIVED` cannot be passed on creation. |
| `GET` | `/v1/admin/courses/{id}` | — | Returns a single course by `public_id` with its dynamic `batch_count`. |
| `PATCH` | `/v1/admin/courses/{id}` | — | Updates name, description, or status with lifecycle validation and pessimistic locking. |

### Batch Management Endpoints

| Method | Endpoint | Query Parameters | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/v1/admin/batches` | `course_id`, `status` | Returns batches with course metadata (`course_public_id`, `course_name`), ordered by `created_at DESC, id DESC`. |
| `POST` | `/v1/admin/batches` | — | Creates a new cohort. Amount must be $>0$. Validates date ranges (`ends_at >= starts_at`). |
| `GET` | `/v1/admin/batches/{id}` | — | Returns a single batch by `public_id` with parent course information. |
| `PATCH` | `/v1/admin/batches/{id}` | — | Updates batch title, fee, date ranges, status, or parent course (with payment session checks). |

---

## 3. Implemented File Inventory

### Backend Repositories & Services
* `backend/app/repositories/course_repository.py`:
  - `list_with_batch_counts(db, status)`: Single outer-join query aggregating batch counts efficiently without N+1 overhead.
  - `get_by_public_id_with_batch_count(db, public_id)`: Fetches single course with grouped batch count.
  - `get_by_public_id_for_update(db, public_id)`: Acquires pessimistic write lock on course row.
* `backend/app/repositories/batch_repository.py`:
  - `list_all_with_course(db, course_id, status)`: Joined load with `Course` entity for atomic metadata retrieval.
  - `get_by_public_id_for_update(db, public_id)`: Isolated `with_for_update()` locking without outer joins.
  - `has_payment_sessions(db, batch_id)`: Checks for payment session existence before allowing course reassignment.
* `backend/app/services/course_service.py`:
  - Enforces `Course` state machine (`ACTIVE` $\leftrightarrow$ `INACTIVE` $\rightarrow$ `ARCHIVED`), trims whitespace, prevents archived mutation.
* `backend/app/services/batch_service.py`:
  - Enforces `Batch` state machine, positive amount constraints, start/end date logic, and course reassignment payment guard.
* `backend/app/schemas/course.py` & `backend/app/schemas/batch.py`:
  - Strict Pydantic models with `CourseStatus` and `BatchStatus` string enums (`ACTIVE`, `INACTIVE`, `ARCHIVED`).
* `backend/app/api/v1/courses.py` & `backend/app/api/v1/batches.py`:
  - RESTful FastAPI routers injected with `require_admin` dependency and `db` session handling.

### Frontend Components & Pages
* `frontend/src/types/course.ts` & `frontend/src/types/batch.ts`:
  - TypeScript interfaces for Course and Batch entities, DTOs, and status enums.
* `frontend/src/services/courseApi.ts` & `frontend/src/services/batchApi.ts`:
  - Type-safe HTTP clients communicating with `/v1/admin/courses` and `/v1/admin/batches`.
* `frontend/src/components/AdminNav.tsx`:
  - Global navigation bar providing fast tab-switching between Dashboard, Courses, and Batches.
* `frontend/src/pages/AdminCoursesPage.tsx` (`/upi/admin/courses`):
  - Course listing with status filters, batch counts, Create/Edit modals, and in-app Archive Confirmation Modal.
* `frontend/src/pages/AdminBatchesPage.tsx` (`/upi/admin/batches`):
  - Batch listing with course dropdown filters, status pills, Create/Edit modals, and in-app Archive Confirmation Modal.
* `frontend/src/app/App.tsx`:
  - Mounted routes for `/upi/admin/courses` and `/upi/admin/batches` inside protected route guards.

---

## 4. Key Fixes & Hardening (Phase 4 Refinements)

1. **Transactional Unit of Work**:
   - Updated `database.py` `get_db_session()` dependency to execute `await session.commit()` on successful request completion.
2. **Single-Flight Refresh Mutex (`apiClient.ts`)**:
   - Encapsulated `/v1/auth/refresh` inside a singleton `refreshPromise` to eliminate race conditions under React StrictMode mounting.
3. **Dedicated In-App Confirmation Modals**:
   - Replaced native `window.confirm()` popups with React confirmation modals to prevent browser popup suppression.
4. **Universal Cookie Scoping (`Path=/`)**:
   - Adjusted `samagra_refresh` cookie path to `/` to ensure reliable credential transmission across all proxy and dev routes.

---

## 5. Verification & Testing Matrix (84 Tests)

All tests pass inside Docker against PostgreSQL 16:

```bash
docker compose run --rm backend pytest tests/ -v
======================= 84 passed in 25.77s ========================
```

### Test Suites Breakdown
* **Course Management API Suite** (`tests/test_courses_api.py`): **12/12 PASSED**
  - Create course (default active, explicit inactive, whitespace rejection, archived rejection).
  - List courses with dynamic batch counts and deterministic ordering.
  - Status filtering (`ACTIVE`, `INACTIVE`, `ARCHIVED`).
  - Single course fetch & 404 handling.
  - Course lifecycle transitions (`ACTIVE` $\rightarrow$ `INACTIVE` $\rightarrow$ `ARCHIVED`).
  - Terminal archival protection (rejects reactivation & mutation).
  - Unauthenticated route 401 guard verification.
* **Batch Management API Suite** (`tests/test_batches_api.py`): **15/15 PASSED**
  - Create batch (default active, explicit inactive, archived rejection).
  - Creation under inactive course (allowed) vs archived course (rejected).
  - Positive amount constraint ($>0$) and date range constraint (`ends_at >= starts_at`).
  - Batch list filtering by course and status.
  - Batch lifecycle state machine (`ACTIVE` $\leftrightarrow$ `INACTIVE` $\rightarrow$ `ARCHIVED`).
  - Terminal archival protection.
  - Batch reassignment allowed when zero payment sessions exist vs forbidden (409) when payment sessions exist.
  - Unauthenticated route 401 guard verification.
* **Historical Snapshot Invariance** (`tests/test_phase4_snapshot_invariance.py`): **1/1 PASSED**
  - Confirms payment session snapshots remain unchanged when course or batch names and amounts are modified.
* **Regression Suites (Phases 1–3)**: **56/56 PASSED**
  - Argon2id password hashing, JWT claims, sliding-window rate limiting, token rotation, and concurrency row-locking.

### Frontend Compilation & Live Browser Verification
* **TypeScript & Vite Build**: `tsc -b && vite build` passed cleanly with 0 errors.
* **End-to-End Browser Session**:
  - Successfully logged in, created courses and batches, refreshed pages with session persistence, and archived entities via custom confirmation modals.
