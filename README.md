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

### Persistence Verification Procedure
To verify that PostgreSQL data survives container deletion:
```bash
# 1. Start containers
docker compose up -d

# 2. Insert test table
docker compose exec postgres psql -U app_user -d training_payments -c \
  "CREATE TABLE persistence_test (id serial primary key, note text); INSERT INTO persistence_test (note) VALUES ('verified');"

# 3. Destroy containers
docker compose down

# 4. Recreate containers
docker compose up -d

# 5. Verify test data still exists
docker compose exec postgres psql -U app_user -d training_payments -c \
  "SELECT * FROM persistence_test;"

# 6. Clean up test table
docker compose exec postgres psql -U app_user -d training_payments -c \
  "DROP TABLE persistence_test;"
```
