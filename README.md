# Samagra UPI Automation — Platform (Phases 1 – 10)

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
| **Phase 1** | Platform Infrastructure | ✅ Completed | Docker 3-container topology, non-root security, host Caddy integration. |
| **Phase 2** | Database Foundation | ✅ Completed | PostgreSQL 16 schema, Alembic migrations, whole-rupee monetary types. |
| **Phase 3** | Admin Auth & Security | ✅ Completed | Argon2id password hashing, JWT Bearer tokens, HTTP-only refresh cookies. |
| **Phase 4** | Course & Batch Management | ✅ Completed | Course & cohort CRUD, status state machines, financial snapshot invariance. |
| **Phase 5** | Public Registration | ✅ Completed | Public checkout registration, input validation, rate-limiting safeguards. |
| **Phase 6** | UPI Payment Session & QR | ✅ Completed | Dynamic UPI link generation, QR codes, immutable financial snapshots. |
| **Phase 7** | UTR Submission & WhatsApp | ✅ Completed | Optional UTR submission, row locking concurrency, WhatsApp link generation. UTR is no longer required — reconciliation matches by reference code + amount. |
| **Phase 8** | Admin Payment Dashboard | ✅ Completed | Paginated admin dashboard, filters, submission audit history inspection. |
| **Phase 9** | Statement Import System | ✅ Completed | Google Pay & Bank CSV/XLSX multi-sheet parser, position mapping, deduplication key calculation, null reference filtering, import deletion. |
| **Phase 10** | Reconciliation Engine | ✅ Completed | Deterministic batch-scoped matching engine, Match button in Admin Workspace, auto-APPROVED status on match, matched badges in Public Registrations table. |

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

---

## 10. Reconciliation Engine (Phase 10)

The Phase 10 Reconciliation Engine enables administrators to match bank statement transactions against registered participant payments with a single click.

### How It Works

1. **Import a Bank Statement** — Upload a CSV or XLSX file via the Statement Import section.
2. **Navigate to a Batch Workspace** — Open any batch in the Admin Workspace.
3. **Select Statement + Click Match** — The top-right area of the **Public Registrations & Payments** table has a statement dropdown and a **Match** button.
4. **Auto-Approve on Match** — Successfully matched sessions are automatically set to `APPROVED` and display a green **✓ Matched** badge inline in the table row.

### Matching Algorithm (Deterministic, Batch-Scoped)

For each bank transaction in the statement, the engine classifies it:

| Result Status | Condition |
| :--- | :--- |
| `MATCHED` | Reference code found in batch AND amount matches. UTR optionally verified if both sides have it. Session auto-approved. |
| `AMOUNT_MISMATCH` | Reference code found but bank amount ≠ expected session amount. |
| `UTR_MISMATCH` | Reference code + amount match, but both UTRs are present and differ. |
| `UNKNOWN_REFERENCE` | Reference code not found in this batch's sessions. |
| `NO_REFERENCE` | Bank transaction has no reference code column value. |
| `DUPLICATE_TRANSACTION` | Same reference code appears more than once in the statement file. |
| `UNMATCHED` | Non-credit transaction (DEBIT / fee). |

> [!NOTE]
> If `direction` is NULL (not mapped during import), the engine safely treats the transaction as CREDIT. This handles split Debit/Credit column formats where only the amount was mapped.

### UTR is Optional

Participants are **not required** to submit a UTR number. The system reconciles using:
- **Required**: Reference Code (generated at QR creation time, embedded in the UPI URI)
- **Required**: Payment Amount (must match the batch fee exactly)
- **Optional**: UTR — if both the bank statement and the participant provided a UTR, they are compared. If either is missing, matching still succeeds based on reference + amount alone.

This change was applied across the entire stack:
- `payment_submissions.utr` column is now `NULL`-able (migration applied)
- `ux_payment_submissions_utr` unique index replaced with a non-unique search index
- `PublicUTRSubmitRequest.utr` is `Optional[str]`
- Public Payment Page shows UTR as **(optional)** with a submit-without-UTR button

### Test Data Tooling (Root Directory)

Three helper scripts at the project root power local manual testing:

| Script | Purpose |
| :--- | :--- |
| [`seed_manual_test_data.py`](./seed_manual_test_data.py) | Creates 3 courses, 3 batches, 6 registered participants, and generates `demo_test_statement.csv` with 9 rows covering all result types |
| [`clean_manual_test_data.py`](./clean_manual_test_data.py) | Removes only seed-tagged test data (courses, batches, sessions, submissions) |
| [`clear_db.py`](./clear_db.py) | Truncates **all** business data while preserving admin user accounts |

**Run from within Docker container:**
```bash
# Seed test data
docker compose exec backend python /app/seed_manual_test_data.py

# Clean only test data
docker compose exec backend python /app/clean_manual_test_data.py

# Wipe all business data (full reset)
docker compose exec backend python /app/clear_db.py
```

### Generated Test CSV Column Layout

`demo_test_statement.csv` uses this column order — map accordingly during Statement Import:

| Col Index | Header | Import Field |
| :--- | :--- | :--- |
| 0 | Date | Transaction Date |
| 1 | Description | Description |
| **2** | **Ref No** | **Reference ID** ← Required |
| **3** | **Direction** | **Direction** (CREDIT/DEBIT) ← Map this! |
| **4** | **Amount** | **Amount** ← Required |
| 5 | UTR | UTR (optional) |

