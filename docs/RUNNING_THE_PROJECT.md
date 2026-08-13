# Running the Samagra UPI Automation Project

Comprehensive operational guide for running, configuring, testing, and deploying the **Samagra UPI Automation** platform.

---

## 1. System Architecture Overview

The Samagra UPI Automation application runs on the **same Ubuntu Droplet** as the existing Task Management application, sharing the host-level **Caddy** reverse proxy.

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

### URL Routing Contract

| Public Path | Internal Routing | Purpose |
| :--- | :--- | :--- |
| `/` | `/var/www/samagra-frontend` | Existing Task Management frontend (**Unchanged**) |
| `/api/*` | `127.0.0.1:8000` | Existing Task Management backend (**Unchanged**) |
| `/upi/*` | `127.0.0.1:8080` (Prod) / `127.0.0.1:5173` (Dev) | UPI React + Vite Frontend |
| `/upi-api/*` | `127.0.0.1:8001` | UPI FastAPI Backend (`/v1/health`, etc.) |

---

## 2. Prerequisites

Ensure the host machine has the following tools installed:
- **Docker Engine** (v24.0+ or v28.0+)
- **Docker Compose** (v2.20+)
- **Git** (for version control)
- *(Optional for host-level reverse proxying)* **Caddy Server** running natively via systemd

---

## 3. Environment Configuration

### Step 1: Initialize the Environment File
Copy the provided `.env.example` template to `.env`:

```bash
cp .env.example .env
```

### Step 2: Configure Variables
Review and update `.env` variables if needed:

```env
# Application Settings
APP_ENV=development
APP_NAME=samagra-upi-automation
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO

# Localhost Port Bindings (Only accessible by Host Caddy)
BACKEND_HOST_PORT=8001
FRONTEND_HOST_PORT=8080

# PostgreSQL Configuration
POSTGRES_DB=training_payments
POSTGRES_USER=app_user
POSTGRES_PASSWORD=change_me_to_a_secure_password
PGDATA=/var/lib/postgresql/data/pgdata
DATABASE_URL=postgresql+asyncpg://app_user:change_me_to_a_secure_password@postgres:5432/training_payments

# CORS Configuration
# In production, browser calls are same-origin through Caddy, so CORS remains empty.
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Frontend Build & Routing Configurations
VITE_BASE_PATH=/upi/
VITE_API_BASE_URL=/upi-api
```

> [!NOTE]
> Never commit `.env` containing sensitive credentials to Git. It is automatically ignored in `.gitignore`.

---

## 4. Running in Development Mode

Development mode mounts local source code into the containers for **live hot-reloading** of both frontend and backend code.

### Start the Stack
```bash
# Build and start all 3 services in background
docker compose up -d --build
```

### Check Service Health
```bash
docker compose ps
```
All three services should display `healthy`:
```text
NAME           IMAGE                             COMMAND                  SERVICE    STATUS
upi-backend    samagra-upi-automation-backend    "uvicorn app.main:ap…"   backend    Up (healthy)
upi-frontend   samagra-upi-automation-frontend   "docker-entrypoint.s…"   frontend   Up (healthy)
upi-postgres   postgres:16.8-alpine              "docker-entrypoint.s…"   postgres   Up (healthy)
```

### Accessing in Development
- **Frontend**: [http://127.0.0.1:5173/upi/](http://127.0.0.1:5173/upi/)
- **Backend Direct Health**: [http://127.0.0.1:8001/v1/health](http://127.0.0.1:8001/v1/health)
- **Database Connectivity Health**: [http://127.0.0.1:8001/v1/health/db](http://127.0.0.1:8001/v1/health/db)

### Stop Development Stack
```bash
docker compose down
```

---

## 5. Running in Production Mode

Production mode uses multi-stage compiled images:
- **Frontend**: Compiled static assets served via lightweight `nginx:1.27-alpine` on port 80 (bound to `127.0.0.1:8080`).
- **Backend**: Python 3.12 executed as non-root user `appuser` (UID 10001) on `127.0.0.1:8001`.
- **PostgreSQL**: Bound to private Docker network `app-network`, persisted to `./docker/postgres/data`.

### Start the Production Stack
```bash
docker compose -f compose.yaml -f compose.production.yaml up -d --build
```

### Check Production Status
```bash
docker compose -f compose.yaml -f compose.production.yaml ps
```

### Accessing in Production
- **Frontend Container**: `http://127.0.0.1:8080/` (or `http://127.0.0.1:8080/healthz`)
- **Backend Container**: `http://127.0.0.1:8001/v1/health`
- **Public Domain**: `http://<YOUR_SERVER_IP>/upi/` (via Host Caddy)

### Stop Production Stack
```bash
docker compose -f compose.yaml -f compose.production.yaml down
```

---

## 6. Host Caddy Integration & Reverse Proxying

The Droplet uses a native systemd Caddy server. **Do not install or run Caddy inside Docker.**

### Step 1: Edit `/etc/caddy/Caddyfile`
Insert the following snippet inside your primary site block in `/etc/caddy/Caddyfile`, **before** the generic fallback handler:

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
```bash
# 1. Validate configuration syntax
sudo caddy validate --config /etc/caddy/Caddyfile

# 2. Gracefully reload Caddy without downtime
sudo systemctl reload caddy
```

### Step 3: Test Public Endpoints
```bash
# Test Frontend
curl -I http://<SERVER_IP>/upi/

# Test Backend API
curl http://<SERVER_IP>/upi-api/v1/health

# Test Database API Connectivity
curl http://<SERVER_IP>/upi-api/v1/health/db
```

---

## 7. PostgreSQL Persistence & Permissions

### Host Bind Mount Location
PostgreSQL data files are stored on the host filesystem at:
```text
./docker/postgres/data/pgdata/
```

### Host Permissions Setup (Linux Droplet)
PostgreSQL inside the container runs as the `postgres` user with `UID 999`.

To ensure proper permissions on Linux:
```bash
# Create directory
mkdir -p docker/postgres/data

# Assign ownership to UID 999 (PostgreSQL daemon user)
sudo chown -R 999:999 docker/postgres/data
sudo chmod 700 docker/postgres/data
```
> [!CAUTION]
> Never use `chmod 777`. The `chown 999:999` approach gives the container daemon exclusive permissions without exposing files to other users.

### Database Backups (Logical `pg_dump`)
Do not copy live files from `./docker/postgres/data` while the database is running. Instead, create consistent logical SQL backups using `pg_dump`:

```bash
docker compose exec -T postgres pg_dump -U app_user training_payments > backup_$(date +%F_%H%M%S).sql
```

To restore a backup:
```bash
docker compose exec -T postgres psql -U app_user -d training_payments < backup_file.sql
```

---

## 8. Automated Tests & Quality Checks

### Run Backend Tests in Container
Execute the complete pytest test suite directly inside the running backend container:

```bash
docker compose exec backend pytest -o cache_dir=/tmp/.pytest_cache tests/ -v
```

Output:
```text
============================= test session starts ==============================
tests/test_config.py::test_default_settings PASSED                       [ 20%]
tests/test_config.py::test_cors_origins_parsing PASSED                   [ 40%]
tests/test_health.py::test_app_health_endpoint PASSED                    [ 60%]
tests/test_health.py::test_database_health_endpoint_success PASSED       [ 80%]
tests/test_health.py::test_database_health_endpoint_failure PASSED       [100%]
============================== 5 passed in 0.68s ===============================
```

### Run Frontend Type Check & Build Locally
```bash
cd frontend
npm install
npm run build
```

---

## 9. Common Operational Commands

### View Logs
```bash
# Stream all logs
docker compose logs -f

# Stream backend logs only
docker compose logs -f backend

# Stream postgres logs only
docker compose logs -f postgres

# Stream frontend logs only
docker compose logs -f frontend
```

### Restart a Specific Service
```bash
# Restart backend
docker compose restart backend

# Restart frontend
docker compose restart frontend
```

### Connect to PostgreSQL Interactive Shell (`psql`)
```bash
docker compose exec postgres psql -U app_user -d training_payments
```

---

## 10. Security & Negative Isolation Verification

Verify that application containers are NOT exposed directly to the public internet:

```bash
# From an external machine, these should be rejected/timeout:
curl http://<SERVER_PUBLIC_IP>:8001/v1/health   # -> Connection refused
curl http://<SERVER_PUBLIC_IP>:8080/           # -> Connection refused
curl http://<SERVER_PUBLIC_IP>:5432/           # -> Connection refused
```

Only the Host Caddy on port 80/443 forwards requests to the internal services.
