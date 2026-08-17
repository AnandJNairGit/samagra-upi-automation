# Samagra UPI Automation — Platform Foundation (Phase 1)

Production-oriented foundation for the UPI training payment collection and reconciliation platform.

---

## 1. Architecture Overview

This application runs on the **same Ubuntu Droplet** as the existing Task Management application, sharing the host-level **Caddy** reverse proxy.

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

### URL Namespace & Routing Contract

| Public Route | Target | Description |
| :--- | :--- | :--- |
| `/` | Host Static Files (`/var/www/samagra-frontend`) | Existing Task Management frontend (**Unchanged**) |
| `/api/*` | `127.0.0.1:8000` | Existing Task Management backend (**Unchanged**) |
| `/upi/*` | `127.0.0.1:8080` (Prod) / `127.0.0.1:5173` (Dev) | UPI Vite + React Frontend container |
| `/upi-api/*` | `127.0.0.1:8001` | UPI FastAPI Backend container (`/v1/health`, etc.) |

---

## 2. Docker Services

The UPI Docker stack contains **exactly three services**:
1. **`frontend`**: Vite + React + TypeScript running in a multi-stage container (served via lightweight `nginx:1.27-alpine` in production).
2. **`backend`**: FastAPI running on Python 3.12 (pinned `python:3.12-slim-bookworm`) executed by a non-root system user (`appuser` UID 10001).
3. **`postgres`**: Pinned `postgres:16.8-alpine` with host bind-mounted persistence.

There is **no Caddy container** inside Docker. Host Caddy handles all external TLS and reverse proxying.

---

## 3. Host Caddy Integration

The existing host Caddy service runs natively via systemd. **Do not install or run Caddy inside Docker.**

### Step 1: Update `/etc/caddy/Caddyfile`
Add the following snippet inside your site block in `/etc/caddy/Caddyfile`, placed **before** the generic static fallback handler:

```caddyfile
# UPI Backend API Handler
handle_path /upi-api/* {
    reverse_proxy 127.0.0.1:8001
}

# UPI Frontend Static/SPA Handler
handle_path /upi/* {
    reverse_proxy 127.0.0.1:8080
}
```

### Step 2: Validate and Reload Caddy
Always validate the Caddyfile before applying changes to prevent downtime:

```bash
# 1. Validate configuration syntax
sudo caddy validate --config /etc/caddy/Caddyfile

# 2. Gracefully reload Caddy without downtime
sudo systemctl reload caddy
```

---

## 4. PostgreSQL Persistence & Host Bind Mount

### Host Bind Mount Location
PostgreSQL data is stored on the host filesystem at:
```text
./docker/postgres/data/
```
which is mounted into the container at:
```text
/var/lib/postgresql/data
```

> [!IMPORTANT]
> - This directory contains active PostgreSQL database files.
> - It is intentionally excluded from version control via `.gitignore`.
> - Do not delete this directory unless you intentionally want to destroy the database.

### Filesystem Permissions (Linux)
The PostgreSQL container runs as the `postgres` user with `UID:GID 999:999`.

When setting up on Linux, ensure the host directory has the correct ownership:
```bash
# Create directory if not present
mkdir -p docker/postgres/data

# Assign ownership to PostgreSQL container user (UID 999)
sudo chown -R 999:999 docker/postgres/data
sudo chmod 700 docker/postgres/data
```
*Never use `chmod 777`.* Setting `chown 999:999` allows the PostgreSQL daemon full access while restricting other users.

### Database Backups
Copying live files from `./docker/postgres/data` while PostgreSQL is running is **not** a valid backup strategy and can result in corrupted tablespaces.

Use PostgreSQL-aware logical backups via `pg_dump`:
```bash
docker compose exec -T postgres pg_dump -U app_user training_payments > backup_$(date +%F_%T).sql
```

---

## 5. Quick Start & Docker Operations

### Initial Setup
1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```
2. Adjust variables in `.env` if necessary.

### Development Mode (with hot-reloading)
```bash
# Start all 3 services in development mode
docker compose up -d --build

# View container status and health
docker compose ps

# Follow logs
docker compose logs -f

# Follow backend logs specifically
docker compose logs -f backend

# Follow postgres logs specifically
docker compose logs -f postgres

# Stop development stack
docker compose down
```

### Production Mode
```bash
# Build and run with production override
docker compose -f compose.yaml -f compose.production.yaml up -d --build

# View running production containers
docker compose -f compose.yaml -f compose.production.yaml ps

# Stop production stack
docker compose -f compose.yaml -f compose.production.yaml down
```

---

## 6. Security & Negative Exposure Verification

All application ports are bound strictly to `127.0.0.1` (localhost):
- **Frontend**: Bound to `127.0.0.1:8080` (prod) or `127.0.0.1:5173` (dev).
- **Backend**: Bound to `127.0.0.1:8001`.
- **PostgreSQL**: Internal to `app-network` (no host port exposed).

### Verify Negative Exposure:
Ensure that direct external access to backend and database ports is blocked:
```bash
# Should NOT be reachable from outside the server:
curl http://<SERVER_PUBLIC_IP>:8001/v1/health   # -> Connection refused / timeout
curl http://<SERVER_PUBLIC_IP>:8080/           # -> Connection refused / timeout
```
Traffic is only accessible when routed through Host Caddy:
```bash
curl http://<SERVER_PUBLIC_IP>/upi/
curl http://<SERVER_PUBLIC_IP>/upi-api/v1/health
curl http://<SERVER_PUBLIC_IP>/upi-api/v1/health/db
```

---

## 7. Verification & Health Checks

### Container Health Checks
All three containers implement automated Docker health checks:
- `postgres`: `pg_isready -U app_user -d training_payments`
- `backend`: `http://localhost:8000/v1/health`
- `frontend`: `http://localhost:80/healthz` (prod) / `http://localhost:5173/upi/` (dev)

---

## 8. Feature Modules & Implemented Phases

| Phase | Feature Module | Status | Highlights |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Platform Infrastructure | Completed | Docker 3-container topology, non-root security, host Caddy integration. |
| **Phase 2** | Database Foundation | Completed | PostgreSQL 16 schema, Alembic migrations, whole-rupee monetary types. |
| **Phase 3** | Admin Auth & Security | Completed | Argon2id password hashing, JWT Bearer tokens, HTTP-only refresh cookies. |
| **Phase 4** | Course & Batch Management | Completed | Course & cohort CRUD, status state machines, financial snapshot invariance. |
| **Phase 5** | Public Registration | Completed | Public checkout registration, input validation, rate-limiting safeguards. |
| **Phase 6** | UPI Payment Session & QR | Completed | Dynamic UPI link generation, QR codes, immutable financial snapshots. |
| **Phase 7** | UTR Submission & WhatsApp | Completed | Unique UTR submission, row locking concurrency, WhatsApp link generation. |
| **Phase 8** | Admin Payment Dashboard | Completed | Paginated admin dashboard, filters, submission audit history inspection. |
| **Phase 9** | Statement Import System | Completed | Google Pay & Bank CSV/XLSX multi-sheet parser, position mapping, deduplication key calculation, null reference filtering, import deletion. |

---

## 9. Statement Import System (Phase 9)

The Phase 9 Statement Import system empowers administrators to upload Google Pay or bank statement export files (`.csv` and multi-sheet `.xlsx` Excel workbooks) to prepare bank transactions for reconciliation in Phase 10.

### Key Capabilities:
1. **Multi-Format Parsing**: Extracts text from `.csv` files and multi-sheet Excel workbooks (`openpyxl`).
2. **Position-Based Column Mapping**: Maps columns using 0-based index numbers (`column_index`) to handle varying bank export column orders.
3. **Two-Step Workflow**: Step 1 Preview generates a 30-minute preview token with zero DB writes; Step 2 Confirm processes candidate rows.
4. **File-Independent Deduplication**: Computes SHA-256 fingerprint hashes (`source_transaction_key`) using normalized transaction data fields so duplicate rows across overlapping monthly statement files are identified and skipped.
5. **Null Reference Row Exclusion**: Rows missing a valid Payment Reference Code are excluded from persistence and logged under `rows_without_reference`.
6. **Import Deletion**: Delete endpoint `DELETE /v1/admin/statement-imports/{public_id}` and UI action modal permanently deletes statement imports and cascade deletes all linked bank transactions.
7. **Accountant-Friendly UI**: Simple accounting terminology (`TOTAL ENTRIES`, `NEW TRANSACTIONS`, `SKIPPED (DUPES)`, `MISSING REF CODE`) with collapsible technical details.

