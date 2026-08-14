# Phase 3 Implementation Plan & Execution Summary

**Phase**: 3 — Admin Authentication & Authorization  
**Status**: Completed & Verified  
**Date**: August 2026  
**Target Platform**: FastAPI, PostgreSQL 16 Alpine with SQLAlchemy 2.x, Alembic, React 18 + TypeScript + Vite.

---

## 1. Primary Objectives & Architectural Mandates

Phase 3 establishes a secure, production-grade authentication and authorization foundation for administrative operators of the Samagra UPI Automation platform.

### Core Security Principles & Decisions
1. **Password Hashing with Argon2id**:
   - Pinned parameters: `time_cost=3`, `memory_cost=65536` KiB (64 MB), `parallelism=4`, `hash_len=32`, `salt_len=16`.
   - **Timing-Attack Defense**: Nonexistent user lookups execute against a precomputed dummy Argon2id hash (`DUMMY_ARGON2_HASH`) via the identical verification pathway before raising a generic `AuthenticationError("Invalid email or password.")`.

2. **Dual-Token Architecture & Memory Isolation**:
   - **Access Tokens**: Short-lived JWTs (15 minutes validity) signed with HMAC-SHA256 (`HS256`). Contain claims `sub`, `public_id`, `token_type="access"`, `iat`, and `exp`. Held strictly in React memory state; zero persistence in `localStorage`, `sessionStorage`, or IndexedDB.
   - **Refresh Tokens**: Long-lived composite tokens (7 days validity) stored in `HttpOnly`, `SameSite=Lax`, `Path=/upi-api/` cookies (`Secure=True` in production).

3. **Composite Refresh Token & Deterministic Replay Protection**:
   - Composite structure: `<session_public_id>.<random_secret>` ($\ge 256$ bits entropy via `secrets.token_urlsafe(32)`).
   - PostgreSQL stores only `SHA256(random_secret)` in `admin_sessions.refresh_token_hash`.
   - **Atomic Rotation & Replay Detection**:
     1. Incoming token is parsed to locate `session_public_id` and `raw_secret`.
     2. Session row is locked via `SELECT ... FROM admin_sessions WHERE public_id = :id FOR UPDATE`.
     3. If `SHA256(raw_secret)` matches current hash $\rightarrow$ Rotate secret to $S_{new}$, update `refresh_token_hash = SHA256(S_{new})`, update `last_used_at = now()`, issue new access token.
     4. If hash mismatches $\rightarrow$ **Replay Detected!** Immediately set `session.revoked_at = now()`, write audit log `ADMIN_REFRESH_REPLAY_DETECTED`, and reject request (`RefreshTokenReplayError`).
     5. Competing concurrent refresh requests serialize cleanly: exactly one succeeds and the other triggers replay detection and revocation.

4. **Process-Local Sliding-Window Rate Limiting**:
   - `POST /v1/auth/login`: 5 attempts per 60s per (IP + normalized email).
   - `POST /v1/auth/refresh`: 30 attempts per 60s per IP.
   - Rejections return `HTTP 429 Too Many Requests` with the standard `Retry-After: <seconds>` header.

5. **Database Model & Migration (`0002_admin_sessions`)**:
   - Entity: `AdminSession` with `id BIGINT IDENTITY PK`, `public_id UUID UK`, `admin_user_id BIGINT FK ON DELETE RESTRICT`, `refresh_token_hash VARCHAR(64) UK`, `user_agent TEXT`, `ip_address INET`, `created_at TIMESTAMPTZ`, `last_used_at TIMESTAMPTZ`, `expires_at TIMESTAMPTZ`, `revoked_at TIMESTAMPTZ`.
   - Composite index `(admin_user_id, revoked_at)` and cleanup index on `(expires_at)`.

6. **Single-Flight Refresh Mutex on Frontend**:
   - `apiClient.ts` queues overlapping 401 requests behind an active refresh promise, preventing parallel refresh race conditions.
   - On application load, `AuthContext.tsx` silently attempts session restoration via `/v1/auth/refresh` before rendering protected routes.

---

## 2. Implemented Endpoints

| Method | Endpoint | Authorization | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/v1/auth/login` | None (Public) | Authenticates credentials, generates session, sets `HttpOnly` refresh cookie, and returns access token. |
| `POST` | `/v1/auth/refresh` | `HttpOnly` Cookie | Authenticates solely via cookie, rotates refresh token, and returns new access token. |
| `POST` | `/v1/auth/logout` | `HttpOnly` Cookie | Revokes current session record in PostgreSQL and deletes the refresh cookie. |
| `POST` | `/v1/auth/logout-all` | `Bearer <token>` | Revokes all active sessions for the current admin across all devices and clears cookie. |
| `GET` | `/v1/auth/me` | `Bearer <token>` | Returns administrator profile (`public_id`, `email`, `full_name`, `is_active`, `last_login_at`). |
| `GET` | `/v1/admin/health` | `Bearer <token>` | Protected endpoint verifying live `require_admin` dependency guard. |

---

## 3. Implemented File Inventory

### Backend
* `backend/app/models/admin_session.py`: `AdminSession` SQLAlchemy 2.x declarative entity with `INET` column.
* `backend/app/models/admin_user.py`: Added `sessions` relationship with cascade configurations.
* `backend/alembic/versions/0002_admin_sessions.py`: Reversible database migration adding `admin_sessions`.
* `backend/app/auth/hashing.py`: Argon2id password hashing, dummy verification, SHA-256 secret hashing, and composite token utilities.
* `backend/app/auth/jwt.py`: Access token encoding, decoding, and standard claim verification.
* `backend/app/auth/rate_limiter.py`: Thread-safe sliding-window rate limiter with `Retry-After` calculation.
* `backend/app/auth/dependencies.py`: `get_current_admin`, `require_admin`, `get_auth_service`, `get_client_ip`, `get_user_agent`.
* `backend/app/repositories/admin_session_repository.py`: Persistence methods (`get_by_public_id_for_update`, `revoke_all_for_admin`, `delete_expired_and_revoked`).
* `backend/app/schemas/auth.py`: Pydantic request/response validation schemas.
* `backend/app/services/auth_service.py`: Authentication, session lifecycle, atomic rotation, and replay detection.
* `backend/app/api/v1/auth.py`: Router for `/login`, `/refresh`, `/logout`, `/logout-all`, and `/me`.
* `backend/app/api/v1/admin.py`: Router for protected admin verification (`/admin/health`).
* `backend/scripts/seed_dev.py`: Development admin seeding CLI requiring `DEV_ADMIN_PASSWORD` and refusing execution in production.

### Frontend
* `frontend/src/types/auth.ts`: TypeScript interfaces for Admin, Auth State, and Tokens.
* `frontend/src/services/apiClient.ts`: Single-flight mutex refresh wrapper, 401 retry interceptor, and strict `credentials: 'same-origin'`.
* `frontend/src/context/AuthContext.tsx`: React Context providing in-memory access token, login, logout, and session restore.
* `frontend/src/components/ProtectedRoute.tsx`: Route guard redirecting unauthenticated requests to `/upi/admin/login`.
* `frontend/src/pages/AdminLoginPage.tsx`: Accessible, styled admin authentication portal view.
* `frontend/src/pages/AdminDashboardPage.tsx`: Admin console verifying identity, session status, and live `/v1/admin/health` API status.
* `frontend/src/app/App.tsx`: App router mounting protected `/upi/admin` dashboard and public `/upi/admin/login`.

---

## 4. Verification & Testing Matrix (56 Tests)

### Pytest Execution Results
Executed via `docker compose exec backend pytest -o cache_dir=/tmp/.pytest_cache tests/ -v`:
- **Hashing & Crypto**: `tests/test_hashing.py` (Argon2id hashing, dummy password verification, secret hashing, composite token parsing & validation).
- **JWT & Claims**: `tests/test_jwt.py` (Access token encoding, decoding, expired token rejection, signature verification, malformed token handling).
- **Service Workflows**: `tests/test_auth_service.py` (Admin authentication, timing attack defense, session lifecycle, token rotation, replay detection revocation, multi-session revocation).
- **HTTP Endpoints**: `tests/test_auth_endpoints.py` (Login success, generic failure errors, rate limiting 429 + Retry-After, cookie-based refresh & logout, protected route guards).
- **Live Concurrency & Row Locking**: `tests/test_auth_concurrency.py` (`test_concurrent_refresh_token_rotation_row_locking` verifying simultaneous token refreshes serialize via `SELECT ... FOR UPDATE`, resulting in exactly 1 success and 1 replay detection).
- **Repository Operations**: `tests/test_repositories.py` (Admin session CRUD, row locking, and cleanup queries).
- **Configuration**: `tests/test_config.py` (JWT secret length validation, cookie secure resolution).
- **Full Regression**: Verified all Phase 2 constraint, model, snapshot, and submission workflow tests continue to pass.

### Migration & Build Verification
1. **Alembic Reversibility**: `alembic upgrade head` $\rightarrow$ `alembic downgrade -1` $\rightarrow$ `alembic upgrade head` tested successfully.
2. **Frontend Compilation**: `tsc -b && vite build` completed in 695ms with zero errors.
3. **Live Browser Verification**: Verified login at `/upi/admin/login`, redirect to `/upi/admin`, and authorized `/v1/admin/health` communication.
