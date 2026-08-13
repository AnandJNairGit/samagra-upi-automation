# Phase 1 Implementation Plan & Execution Summary

**Phase**: 1 — Docker + Basic Application Skeleton  
**Status**: Completed & Verified  
**Date**: August 2026  
**Target Platform**: Single Ubuntu Droplet hosting both existing Task Management app and new Samagra UPI Automation application.

---

## 1. Architectural Mandate

The primary goal of Phase 1 was to establish a production-quality, modular monolith foundation without implementing business logic (auth, courses, payments, reconciliation, etc.).

### Key Constraints & Architecture Decisions
1. **Shared Droplet Co-existence**: The UPI stack runs alongside the existing Task Management application.
2. **Single Host Reverse Proxy (Caddy)**: Caddy runs natively on the host via systemd on ports 80/443. **No Caddy Docker container** exists in the UPI application stack.
3. **Task Management Application Untouched**:
   - `/` -> `/var/www/samagra-frontend` (Task frontend)
   - `/api/*` -> `127.0.0.1:8000` (Task backend)
4. **UPI Dedicated Namespace**:
   - `/upi/*` -> `127.0.0.1:8080` (UPI Frontend container)
   - `/upi-api/*` -> `127.0.0.1:8001` (UPI Backend container)
5. **PostgreSQL Persistence via Host Bind Mount**:
   - Data stored permanently on the host at `./docker/postgres/data/pgdata`.
   - Bound to container at `/var/lib/postgresql/data`.
   - No named volumes or anonymous volumes used.
6. **Negative Security (Localhost-Only Bindings)**:
   - Backend bound to `127.0.0.1:8001`
   - Frontend bound to `127.0.0.1:8080` (Prod) / `127.0.0.1:5173` (Dev)
   - PostgreSQL strictly internal to private bridge `app-network` (no published host port).

---

## 2. Architecture Diagram

```text
                               PUBLIC IP (Internet)
                                        |
                                        v
                               Existing Host Caddy
                                 (Port 80 / 443)
                                        |
        +-------------------------------+-------------------------------+
        |                                                               |
        v                                                               v
 Existing Task App (UNCHANGED)                                     New UPI App
 /        → /var/www/samagra-frontend                              /upi/*     → 127.0.0.1:8080 (Frontend container)
 /api/*   → 127.0.0.1:8000 (Task Backend)                          /upi-api/* → 127.0.0.1:8001 (UPI Backend)
                                                                        |
                                                           +------------+------------+
                                                           |                         |
                                                           v                         v
                                                   Frontend (Vite/React)     Backend (FastAPI)
                                                   Container (Port 80)       Container (Port 8000)
                                                                                     |
                                                                                     v
                                                                             PostgreSQL Container
                                                                                (Internal 5432)
                                                                                     |
                                                                                     v  (Host Bind Mount)
                                                                            ./docker/postgres/data
```

---

## 3. Implemented Components & Files

### Configuration & Root Infrastructure
- [compose.yaml](file:///c:/Users/Anand%20j%20nair/Documents/Samagra/Samagra-upi-automation/compose.yaml): Primary/development Docker Compose configuration with volume mounts for live hot-reload, health checks, and localhost port mappings.
- [compose.production.yaml](file:///c:/Users/Anand%20j%20nair/Documents/Samagra/Samagra-upi-automation/compose.production.yaml): Production Docker Compose override utilizing compiled static Nginx frontend, non-root backend runtime, and `!override` directives.
- [.env.example](file:///c:/Users/Anand%20j%20nair/Documents/Samagra/Samagra-upi-automation/.env.example): Complete environment configuration template with safe defaults.
- [.gitignore](file:///c:/Users/Anand%20j%20nair/Documents/Samagra/Samagra-upi-automation/.gitignore): Strictly ignores `.env`, `node_modules`, `dist`, `__pycache__`, and `docker/postgres/data/*`.
- [caddy/Caddyfile.snippet](file:///c:/Users/Anand%20j%20nair/Documents/Samagra/Samagra-upi-automation/caddy/Caddyfile.snippet): Snippet for `/etc/caddy/Caddyfile` using `handle_path` to proxy `/upi/*` and `/upi-api/*`.
- [docker/postgres/data/.gitkeep](file:///c:/Users/Anand%20j%20nair/Documents/Samagra/Samagra-upi-automation/docker/postgres/data/.gitkeep): Git preservation placeholder.

### Backend (FastAPI + Python 3.12)
- [backend/Dockerfile](file:///c:/Users/Anand%20j%20nair/Documents/Samagra/Samagra-upi-automation/backend/Dockerfile): Multi-stage build using `python:3.12-slim-bookworm`, non-root user `appuser` (UID 10001), healthcheck on `/v1/health`.
- [backend/requirements.txt](file:///c:/Users/Anand%20j%20nair/Documents/Samagra/Samagra-upi-automation/backend/requirements.txt): Exact pinned dependency versions (`fastapi==0.115.8`, `uvicorn==0.34.0`, `sqlalchemy==2.0.38`, `asyncpg==0.30.0`, `pydantic-settings==2.7.1`, `pytest==8.3.4`, `pytest-asyncio==0.25.3`, `httpx==0.28.1`).
- [backend/.dockerignore](file:///c:/Users/Anand%20j%20nair/Documents/Samagra/Samagra-upi-automation/backend/.dockerignore): Excludes test artifacts, cache, and virtual environments.
- [backend/app/main.py](file:///c:/Users/Anand%20j%20nair/Documents/Samagra/Samagra-upi-automation/backend/app/main.py): FastAPI app with async lifespan management and CORS middleware.
- [backend/app/core/config.py](file:///c:/Users/Anand%20j%20nair/Documents/Samagra/Samagra-upi-automation/backend/app/core/config.py): Strongly typed `BaseSettings` schema.
- [backend/app/core/database.py](file:///c:/Users/Anand%20j%20nair/Documents/Samagra/Samagra-upi-automation/backend/app/core/database.py): Async SQLAlchemy engine and connectivity verifier.
- [backend/app/core/logging.py](file:///c:/Users/Anand%20j%20nair/Documents/Samagra/Samagra-upi-automation/backend/app/core/logging.py): Safe structured logging.
- [backend/app/api/v1/health.py](file:///c:/Users/Anand%20j%20nair/Documents/Samagra/Samagra-upi-automation/backend/app/api/v1/health.py): Canonical health endpoints `/v1/health` and `/v1/health/db`.
- [backend/tests/test_health.py](file:///c:/Users/Anand%20j%20nair/Documents/Samagra/Samagra-upi-automation/backend/tests/test_health.py) & [test_config.py](file:///c:/Users/Anand%20j%20nair/Documents/Samagra/Samagra-upi-automation/backend/tests/test_config.py): Async test suite.

### Frontend (Vite + React + TypeScript)
- [frontend/Dockerfile](file:///c:/Users/Anand%20j%20nair/Documents/Samagra/Samagra-upi-automation/frontend/Dockerfile): Multi-stage build with `development` (Node 22) and `production` (`nginx:1.27-alpine` static server on port 80).
- [frontend/.dockerignore](file:///c:/Users/Anand%20j%20nair/Documents/Samagra/Samagra-upi-automation/frontend/.dockerignore): Build context exclusion file.
- [frontend/nginx.conf](file:///c:/Users/Anand%20j%20nair/Documents/Samagra/Samagra-upi-automation/frontend/nginx.conf): Static Nginx config with gzip compression, security headers, and SPA fallback.
- [frontend/vite.config.ts](file:///c:/Users/Anand%20j%20nair/Documents/Samagra/Samagra-upi-automation/frontend/vite.config.ts): Configured with `base: '/upi/'` and dev proxy `/upi-api` -> `http://backend:8000`.
- [frontend/src/app/App.tsx](file:///c:/Users/Anand%20j%20nair/Documents/Samagra/Samagra-upi-automation/frontend/src/app/App.tsx): Clean React UI shell.
- [frontend/src/components/HealthStatus.tsx](file:///c:/Users/Anand%20j%20nair/Documents/Samagra/Samagra-upi-automation/frontend/src/components/HealthStatus.tsx): Live backend and database connectivity monitor with auto-refresh.
- [frontend/src/services/api.ts](file:///c:/Users/Anand%20j%20nair/Documents/Samagra/Samagra-upi-automation/frontend/src/services/api.ts): Centralized API caller.

---

## 4. Verification & Testing Evidence

### 1. Automated Test Suite (Pytest)
```bash
docker compose exec backend pytest -o cache_dir=/tmp/.pytest_cache tests/ -v
```
**Result**: 5 passed in 0.68s
- `tests/test_config.py::test_default_settings` -> PASSED
- `tests/test_config.py::test_cors_origins_parsing` -> PASSED
- `tests/test_health.py::test_app_health_endpoint` -> PASSED
- `tests/test_health.py::test_database_health_endpoint_success` -> PASSED
- `tests/test_health.py::test_database_health_endpoint_failure` -> PASSED

### 2. Frontend Build Check
```bash
cd frontend && npm run build
```
**Result**: TypeScript compilation and Vite build succeeded (`tsc -b && vite build`) emitting assets with `/upi/` base path.

### 3. PostgreSQL Host Bind Mount Persistence Verification
- **Step 1**: Created `persistence_test` table in `training_payments` DB and inserted test record.
- **Step 2**: Executed `docker compose down` (all containers destroyed).
- **Step 3**: Inspected host directory `./docker/postgres/data/pgdata/` to verify physical existence of database cluster files.
- **Step 4**: Executed `docker compose up -d` (recreated containers).
- **Step 5**: Queried `persistence_test` -> record was intact (`phase1_persistence_verified`).
- **Step 6**: Dropped temporary test table.

### 4. Negative Security Check
- `docker port upi-backend` -> `8000/tcp -> 127.0.0.1:8001` (Only localhost)
- `docker port upi-frontend` -> `5173/tcp -> 127.0.0.1:5173` / `80/tcp -> 127.0.0.1:8080` (Only localhost)
- `docker port upi-postgres` -> Empty (No host port exposed, private Docker network only)

---

## 5. Scope Retained for Future Phases

The following features were intentionally excluded from Phase 1 and will be introduced in subsequent phases:
- Phase 2: Database schema models, SQLAlchemy entities, Alembic migrations.
- Phase 3: Authentication, JWT tokens, session management.
- Phase 4: Admin dashboard, course and batch management.
- Phase 5: UPI QR generation, payment session management, UTR validation.
- Phase 6: Reconciliation engine, Google Pay statement parsing, WhatsApp automation.
