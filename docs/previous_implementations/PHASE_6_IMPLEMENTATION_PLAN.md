# Phase 6 Implementation Plan & Execution Summary

**Phase**: 6 — UPI Payment Session + QR  
**Status**: Completed & Verified  
**Date**: August 2026  
**Target Platform**: FastAPI (Python 3.12), PostgreSQL 16 Alpine with SQLAlchemy 2.x (asyncpg), React 18 + TypeScript + Vite (`qrcode.react`).

---

## 1. Primary Objectives & Invariants

Phase 6 implements the server-side payment session generation, unique payment reference generation, UPI Intent URI formulation, dynamic high-resolution QR rendering, and public payment checkout page (`/upi/payment/:paymentSessionPublicId`).

### Core Business Rules & Invariants
1. **Zero Database Migrations**:
   - Reuses the existing `payment_sessions` schema established in Phase 2. No new tables (`payment_links`, `qr_codes`, `participants`) or schema modifications were introduced.
2. **Authoritative Server Data**:
   - The frontend never supplies or controls the `amount_inr`, `course_id`, `batch_id`, `reference_id`, `upi_id`, `payee_name`, or `status`.
   - `amount_inr`, course name, and batch name are strictly derived from the database record of the active batch.
   - Pydantic schema strictly enforces `extra="forbid"` ($\rightarrow$ `422 Unprocessable Entity` on client tampering).
3. **Unique Reference ID Generation**:
   - Format: `<FIRST_NAME_PREFIX>_<PHONE_LAST_4>_<4_CHAR_CRYPTO_RANDOM>` (e.g., `ADITYA_3210_YON2`).
   - Bounded collision retry logic guarantees uniqueness against database constraints.
4. **Standardized UPI Intent URI**:
   - Constructed and URL-encoded strictly on the backend:
     $$\text{upi://pay?pa=samagralearning@ibl\&pn=Samagra\%20Training\&am=2500\&cu=INR\&tn=ADITYA\_3210\_YON2\&tr=ADITYA\_3210\_YON2}$$
   - Encoded directly into the visual QR code without client reconstruction.
5. **Immutable Financial & UPI Snapshots**:
   - `course_name_snapshot`, `batch_name_snapshot`, `amount_inr`, `upi_id_snapshot`, `payee_name_snapshot`, and `upi_uri` are preserved at creation time. Subsequent updates to course or batch metadata do **not** mutate historical payment session snapshots.
6. **Strict Phase 6 / Phase 7 Boundary**:
   - Initial status is strictly `PENDING`.
   - Does **NOT** create `PaymentSubmission` records, accept UTR input, send WhatsApp alerts, or simulate fake payment verification.

---

## 2. Implemented API Endpoints

All Phase 6 endpoints are public, unauthenticated, and rate-limited.

| Method | Endpoint | Rate Limit | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/v1/public/payment-sessions` | 20 req/min per (IP + batch_id) | Creates a new payment session with PENDING status, generates unique reference ID & UPI URI, and saves snapshots. |
| `GET` | `/v1/public/payment-sessions/{session_public_id}` | 60 req/min per IP | Resolves public payment session data (omits internal database IDs and admin metadata) to render the checkout page on fresh load or page refresh. |

---

## 3. Implemented File Inventory

### Backend Components
* `backend/app/core/config.py`:
  - Added `UPI_ID` (default: `"samagralearning@ibl"`), `UPI_PAYEE_NAME` (default: `"Samagra Training"`), and `PAYMENT_SESSION_EXPIRE_MINUTES` (default: `30`).
* `backend/app/services/upi_service.py`:
  - `generate_reference_id(full_name, phone)`: generates unique, readable, uppercase reference IDs.
  - `build_upi_uri(upi_id, payee_name, amount_inr, reference_id)`: formats and URL-encodes the standard UPI intent URI.
* `backend/app/schemas/payment_session.py`:
  - `PaymentSessionCreateRequest`: validates participant input, forbids extra/tampered fields (`extra="forbid"`).
  - `PaymentSessionPublicResponse`: safe public view for rendering payment pages with expiration status.
* `backend/app/services/payment_session_service.py`:
  - `create_payment_session(db, payload)`: transactional creation, active batch verification, authoritative derivation, snapshot persistence.
  - `get_public_payment_session(db, session_public_id)`: safe public lookup for payment page.
* `backend/app/services/exceptions.py`:
  - Added `PaymentSessionUnavailableError` and `PaymentSessionExpiredError`.
* `backend/app/api/v1/public.py`:
  - Added public endpoints `POST /v1/public/payment-sessions` and `GET /v1/public/payment-sessions/{payment_session_public_id}`.
* `backend/tests/test_phase6_payment_session_api.py`:
  - 18 automated integration and regression tests.

### Frontend Components
* `frontend/package.json`:
  - Installed `qrcode.react` (`^4.2.0`) for crisp, SVG-based QR code generation.
* `frontend/src/types/public.ts`:
  - Added `PaymentSessionPublic` interface.
* `frontend/src/services/publicApi.ts`:
  - Added `createPaymentSession` and `fetchPaymentSession`.
* `frontend/src/pages/PublicPaymentPage.tsx`:
  - Mobile-first payment checkout page (`/upi/payment/:paymentSessionPublicId`) rendering program details, amount banner, large SVG QR code, 1-click copy buttons for Reference ID & UPI ID, payment instructions, and expiration handling.
* `frontend/src/pages/PublicRegistrationPage.tsx`:
  - Updated "Continue to Pay" action to invoke `createPaymentSession` and navigate directly to `/upi/payment/:paymentSessionPublicId`.
* `frontend/src/app/App.tsx`:
  - Mounted public route `/upi/payment/:paymentSessionPublicId` (and `/payment/:paymentSessionPublicId`).
* `frontend/src/index.css`:
  - Added styles for the payment checkout card, amount banner, QR container, copyable key cards, and instruction checklist.

---

## 4. Verification & Testing Matrix (117 Tests)

Executed inside Docker against PostgreSQL 16:

```bash
docker compose run --rm backend pytest tests/ -v
====================== 117 passed in 16.40s ======================
```

### Test Suite Breakdown
* **Phase 6 UPI Payment Session Suite** (`tests/test_phase6_payment_session_api.py`): **18/18 PASSED**
  - Payment session creation returns 201 with status `PENDING`.
  - Amount is strictly derived from active batch fee.
  - Client attempts to inject amount, UPI ID, or reference ID are rejected (`422`).
  - All snapshots (`course_name`, `batch_name`, `amount_inr`, `upi_id`, `payee_name`, `upi_uri`) stored accurately.
  - Successive session creations generate unique reference IDs.
  - Nonexistent, inactive, or archived batches return `404`.
  - Inactive or archived courses return `404`.
  - UPI URI semantics and URL encoding validated against standard scheme.
  - Updating Course or Batch records does not mutate existing PaymentSession snapshots.
  - Public payment lookup returns 200 without altering state.
  - Unknown payment session UUID returns `404`.
  - Zero `PaymentSubmission` rows created (Phase 6 boundary enforced).
  - Expiration timestamp triggers `is_expired=True` and `status="EXPIRED"`.
* **Phases 1–5 Regression Suites**: **99/99 PASSED**
  - Public Registration (15 tests), Course & Batch Management, Admin Auth, Refresh Rotation, Constraints, and Snapshot Invariance.

### Frontend Compilation & Live Browser Verification
* **TypeScript & Vite Build**: `tsc -b && vite build` compiled in 1.44s with **0 errors**.
* **Live Browser E2E Session**:
  - Admin copied batch registration link $\rightarrow$ `/upi/register/<batch_public_id>`.
  - Participant ("Aditya Nair") submitted contact details $\rightarrow$ clicked "Continue to Pay".
  - Automatic transition to `/upi/payment/<payment_session_public_id>`.
  - High-res QR code rendered from server-generated UPI URI.
  - Reference ID (`ADITYA_3210_YON2`) and UPI ID (`samagralearning@ibl`) copy buttons tested with visual confirmation.
  - Page refreshed $\rightarrow$ all payment data and QR reloaded seamlessly from backend without error.
