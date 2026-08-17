# Phase 7 — UTR Submission & WhatsApp Deep Link Notification

## 1. Executive Summary

Phase 7 implements the participant's post-payment submission flow and administrator WhatsApp notification in the **Samagra UPI Automation Platform**.

After completing a UPI transfer via dynamic QR code or UPI ID, the participant submits their 12-digit transaction reference number (UTR). The platform validates the UTR, establishes row-level concurrency locks, transitions both `PaymentSession` and `PaymentSubmission` entities to `SUBMITTED`, persists the submission, and generates a pre-filled WhatsApp deep link formatted specifically for institutional administrator notification.

---

## 2. Architectural Design & Security Boundaries

### 2.1 WhatsApp Notification Rule (No Meta Cloud API / No Automated Backend WhatsApp)
As required by platform architecture, the backend **never** sends automated WhatsApp messages, does **not** integrate with WhatsApp Cloud API or Twilio, and requires no API keys or webhook secrets.

Instead, the backend constructs standard, RFC-compliant WhatsApp deep links:
`https://wa.me/<ADMIN_PHONE>?text=<URL_ENCODED_MESSAGE>`

The participant clicks the deep link or the application triggers a browser tab open, passing full payment details directly into the participant's personal WhatsApp client addressed to the institute administrator.

### 2.2 Pre-Filled WhatsApp Notification Template
The message body is formatted with human-readable line breaks and financial snapshot values:

```text
NEW PAYMENT SUBMISSION

Name: {full_name}
Phone: {phone}
Email: {email}

Course: {course_name_snapshot}
Batch: {batch_name_snapshot}
Amount: ₹{amount_inr}

Reference ID: {reference_id}
UTR: {utr}

Payment Status: SUBMITTED
```

### 2.3 Strict Immutability of Financial Snapshots
The WhatsApp notification and submission responses draw exclusively from the immutable snapshot fields created during Phase 6 (`course_name_snapshot`, `batch_name_snapshot`, `amount_inr`, `reference_id`), guaranteeing that subsequent edits to course names or batch tuition fees never mutate or misrepresent historical transactions.

### 2.4 Idempotency, Concurrency & Row-Level Locking
1. **Row-Level Serialization**: `PaymentSubmissionService.submit_utr_by_public_id` queries the payment session using `SELECT ... FOR UPDATE`, serializing concurrent submission attempts on the same checkout session.
2. **Global UTR Uniqueness**: Backed by PostgreSQL unique index `ux_payment_submissions_utr` on `payment_submissions(utr)`. Competing submissions with identical UTR across different sessions trigger `IntegrityError` and return `HTTP 409 Conflict`.
3. **Session Uniqueness**: Backed by PostgreSQL partial unique index `ux_payment_submissions_current` (`payment_session_id WHERE is_current = TRUE`).
4. **Resubmission Compatibility**: If an administrator previously marked a submission `REJECTED`, the session state allows the participant to resubmit a new UTR. The prior submission is deactivated (`is_current = False`), and a fresh submission is created (`is_current = True`).

---

## 3. Database Schema & Migration Status

**0 new migrations were required for Phase 7.**
The existing Phase 2 schema on `payment_submissions` already contains all necessary columns and indexes:
- `id` (BigInteger PK)
- `public_id` (UUID unique)
- `payment_session_id` (FK to `payment_sessions.id`)
- `utr` (VARCHAR unique)
- `status` (VARCHAR, default `SUBMITTED`)
- `is_current` (BOOLEAN, default `True`)
- `submitted_at` (TIMESTAMPTZ, server UTC)
- `reviewed_by` (FK to `admin_users.id`, nullable)
- `reviewed_at` (TIMESTAMPTZ, nullable)
- `rejection_reason` (TEXT, nullable)
- `created_at`, `updated_at`

---

## 4. API Endpoints

### 4.1 Submit Transaction Reference (UTR)
- **Method / Path**: `POST /v1/public/payment-sessions/{payment_session_public_id}/submissions`
- **Rate Limit**: 10 requests / 60 seconds per IP + session ID
- **Request Body**:
```json
{
  "utr": "123456789012"
}
```
- **Response (`201 Created`)**:
```json
{
  "payment_session_public_id": "3aa13560-4368-4a9d-a790-c536f4116f04",
  "submission_public_id": "8fa112e4-9844-48f1-9b16-f3b145610ef0",
  "status": "SUBMITTED",
  "utr_masked": "1234••••9012",
  "submitted_at": "2026-08-16T18:27:00.000Z",
  "whatsapp_url": "https://wa.me/919876543210?text=..."
}
```
- **Error Responses**:
  - `400 Bad Request`: Expired payment session.
  - `404 Not Found`: Non-existent payment session.
  - `409 Conflict`: Duplicate UTR or session already submitted.
  - `422 Unprocessable Entity`: Blank, whitespace, short (< 4 chars), or oversized (> 100 chars) UTR.
  - `429 Too Many Requests`: Rate limit exceeded.

### 4.2 Fetch Public Payment Session (Updated)
- **Method / Path**: `GET /v1/public/payment-sessions/{payment_session_public_id}`
- **Enhancement**: When `session.status == "SUBMITTED"`, automatically resolves `current_submission` and populates `submission_public_id`, `utr_masked`, `submitted_at`, and `whatsapp_url`. Allows seamless page reload persistence.

---

## 5. Verification & Test Coverage

### 5.1 Automated Backend Pytest Suite
- **Total Tests**: 132 passed (100% pass rate).
- **Phase 7 Test File**: `backend/tests/test_phase7_utr_whatsapp_api.py`
  - Valid UTR submission (201 Created).
  - Status synchronization (`PENDING` $\rightarrow$ `SUBMITTED`).
  - Server-side UTC timestamping.
  - Validation: empty, whitespace, short, oversized UTRs (422).
  - Duplicate UTR protection across different payment sessions (409).
  - Resubmission rejection on already submitted sessions (409).
  - Non-existent sessions (404) and expired sessions (400).
  - Financial snapshot invariance.
  - WhatsApp URL formatting and URL encoding.
  - Snapshot resilience against parent batch modifications.
  - `GET /v1/public/payment-sessions/{id}` submitted state persistence.
  - Live concurrency: simultaneous duplicate UTR submissions with row locking.
  - Live concurrency: simultaneous submissions against the same session.

### 5.2 Frontend Build & TypeScript Validation
- `npm run build` completed cleanly in 1.32s with 0 type errors.

### 5.3 Live Browser E2E Verification
Executed via browser subagent recording `phase7_utr_submission_e2e_1786906106202.webp`:
1. Navigated to public batch registration link.
2. Completed participant form (Name, Phone, Email).
3. Proceeded to UPI payment page (`/upi/payment/...`).
4. Entered 12-digit UTR (`987654321098`) and clicked submit.
5. Successfully verified transition to `SUBMITTED` state, masked UTR display (`9876••••1098`), green badge "Payment Submitted", and "Notify Administrator on WhatsApp" deep link button.
6. Refreshed page and verified persistence of submitted state.
