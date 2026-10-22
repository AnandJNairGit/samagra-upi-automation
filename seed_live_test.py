"""
Seed Live Test Data Script for Samagra UPI Automation
=====================================================
Reads course, batch, and participant data from live_test_seed.json,
cleans any previous sessions with the same reference IDs, and injects
the records into PostgreSQL for manual bank statement reconciliation testing.

Usage:
  Direct Python:
    python seed_live_test.py
  Docker Compose:
    docker compose exec backend python /app/seed_live_test.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add backend directory and /app to sys.path
BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR / "backend"

for p in ["/app", str(BACKEND_DIR), str(BASE_DIR), os.getcwd()]:
    if p and p not in sys.path and os.path.exists(p):
        sys.path.insert(0, p)

from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select, delete

from app.models.course import Course
from app.models.batch import Batch
from app.models.payment_session import PaymentSession
from app.models.payment_submission import PaymentSubmission
from app.models.reconciliation_run import ReconciliationRun
from app.models.reconciliation_result import ReconciliationResult


def resolve_json_path() -> Path:
    """Find live_test_seed.json either alongside the script, /tmp, or in /app."""
    if len(sys.argv) > 1 and sys.argv[1].strip():
        candidate = Path(sys.argv[1]).resolve()
        if candidate.exists():
            return candidate

    candidates = [
        BASE_DIR / "live_test_seed.json",
        Path("/tmp/live_test_seed.json"),
        Path("/app/live_test_seed.json"),
        Path("live_test_seed.json").resolve(),
    ]

    for c in candidates:
        if c.exists():
            return c

    print("[ERROR] Could not find 'live_test_seed.json'. Looked in:")
    for c in candidates:
        print(f"  - {c}")
    sys.exit(1)


def get_db_url() -> str:
    """Determine database connection URL for host vs Docker environments."""
    db_url = os.environ.get("DATABASE_URL") or settings.DATABASE_URL
    in_docker = os.path.exists("/.dockerenv")

    # If running directly on host, adjust postgres:5432 to 127.0.0.1:POSTGRES_HOST_PORT
    if not in_docker and "postgres:5432" in db_url:
        host_port = os.environ.get("POSTGRES_HOST_PORT", "5435")
        db_url = db_url.replace("postgres:5432", f"127.0.0.1:{host_port}")

    return db_url


async def main():
    if os.environ.get("SEED_JSON"):
        print("=" * 75)
        print("[*] SEEDING LIVE TEST DATA FOR RECONCILIATION")
        print("=" * 75)
        print("[*] Reading configuration from environment variable SEED_JSON")
        data: Dict[str, Any] = json.loads(os.environ["SEED_JSON"])
    else:
        json_path = resolve_json_path()
        print("=" * 75)
        print("[*] SEEDING LIVE TEST DATA FOR RECONCILIATION")
        print("=" * 75)
        print(f"[*] Reading configuration: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            data: Dict[str, Any] = json.load(f)

    course_name = data.get("course_name", "UPI Live Reconciliation Course")
    course_desc = data.get("course_description", "Course for live UPI statement reconciliation")

    # Support either a list of batches or a single batch definition
    batches_data = []
    if "batches" in data and isinstance(data["batches"], list):
        batches_data = data["batches"]
    elif "batch_name" in data:
        batches_data = [
            {
                "batch_name": data.get("batch_name", "UPI Live Test Batch"),
                "amount_inr": data.get("batch_amount_inr", data.get("amount_inr", 1)),
                "participants": data.get("participants", []),
            }
        ]
    else:
        print("[ERROR] JSON must provide either 'batches' or 'batch_name' with 'participants'.")
        sys.exit(1)

    db_url = get_db_url()
    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    upi_id = getattr(settings, "UPI_ID", "9447126353@ptyes")
    payee_name = getattr(settings, "UPI_PAYEE_NAME", "Samagra Training")

    async with async_session() as db:
        # Collect all reference IDs to guarantee idempotency across multiple runs
        all_refs = []
        for b_info in batches_data:
            for p_info in b_info.get("participants", []):
                ref = str(p_info.get("reference_id", "")).strip()
                if ref:
                    all_refs.append(ref)

        if all_refs:
            print(f"[*] Checking for existing payment sessions with matching reference IDs ({len(all_refs)} refs)...")
            stmt_ref = select(PaymentSession).where(PaymentSession.reference_id.in_(all_refs))
            res_ref = await db.execute(stmt_ref)
            existing_ref_sessions = list(res_ref.scalars().all())

            if existing_ref_sessions:
                s_ids = [s.id for s in existing_ref_sessions]
                print(f"    Cleaning up {len(s_ids)} existing session(s) to allow clean re-seeding...")
                await db.execute(delete(ReconciliationResult).where(ReconciliationResult.payment_session_id.in_(s_ids)))
                await db.execute(delete(PaymentSubmission).where(PaymentSubmission.payment_session_id.in_(s_ids)))
                await db.execute(delete(PaymentSession).where(PaymentSession.id.in_(s_ids)))
                await db.flush()

        # Find or create Course
        stmt_course = select(Course).where(Course.name == course_name)
        res_course = await db.execute(stmt_course)
        course = res_course.scalar_one_or_none()

        if not course:
            course = Course(
                name=course_name,
                description=course_desc,
                status="ACTIVE",
            )
            db.add(course)
            await db.flush()
            print(f"[+] Created Course: '{course.name}' (Public ID: {course.public_id})")
        else:
            print(f"[*] Using existing Course: '{course.name}' (Public ID: {course.public_id})")

        total_seeded_participants = 0
        all_created_records = []

        for b_idx, b_info in enumerate(batches_data):
            batch_name = b_info.get("batch_name", f"Batch {b_idx + 1}")
            batch_amount = int(b_info.get("amount_inr", 1))

            stmt_batch = select(Batch).where(
                Batch.course_id == course.id,
                Batch.name == batch_name,
            )
            res_batch = await db.execute(stmt_batch)
            batch = res_batch.scalar_one_or_none()

            if not batch:
                batch = Batch(
                    course_id=course.id,
                    name=batch_name,
                    amount_inr=batch_amount,
                    status="ACTIVE",
                )
                db.add(batch)
                await db.flush()
                print(f"\n[+] Created Batch: '{batch.name}' | Fee: ₹{batch.amount_inr} (Public ID: {batch.public_id})")
            else:
                batch.amount_inr = batch_amount
                batch.status = "ACTIVE"
                await db.flush()
                print(f"\n[*] Using existing Batch: '{batch.name}' | Fee: ₹{batch.amount_inr} (Public ID: {batch.public_id})")

            participants = b_info.get("participants", [])
            for p_idx, p in enumerate(participants):
                p_name = p.get("name", f"Participant {p_idx + 1}")
                p_phone = str(p.get("phone", f"9876543{b_idx:02d}{p_idx:02d}"))
                p_email = p.get("email", f"p_{b_idx}_{p_idx}@example.com")
                p_ref = str(p.get("reference_id", "")).strip()
                p_amount = int(p.get("amount_inr", batch.amount_inr))
                p_utr = str(p.get("utr", "")).strip() if p.get("utr") else None
                p_status = p.get("status", "SUBMITTED")

                if not p_ref:
                    print(f"    [WARN] Skipping participant '{p_name}' - missing reference_id.")
                    continue

                ps_uri = f"upi://pay?pa={upi_id}&pn={payee_name}&am={p_amount}&tr={p_ref}"

                ps = PaymentSession(
                    full_name=p_name,
                    phone=p_phone,
                    email=p_email,
                    course_id=course.id,
                    batch_id=batch.id,
                    course_name_snapshot=course.name,
                    batch_name_snapshot=batch.name,
                    amount_inr=p_amount,
                    reference_id=p_ref,
                    upi_id_snapshot=upi_id,
                    payee_name_snapshot=payee_name,
                    upi_uri=ps_uri,
                    status=p_status,
                )
                db.add(ps)
                await db.flush()

                sub = PaymentSubmission(
                    payment_session_id=ps.id,
                    utr=p_utr,
                    status=p_status,
                    is_current=True,
                )
                db.add(sub)
                await db.flush()

                total_seeded_participants += 1
                all_created_records.append({
                    "batch": batch.name,
                    "name": p_name,
                    "ref": p_ref,
                    "amount": p_amount,
                    "utr": p_utr or "(none)",
                })

        await db.commit()

    await engine.dispose()

    print("\n" + "=" * 75)
    print(f"[+] SUCCESSFULLY SEEDED {total_seeded_participants} PARTICIPANTS")
    print("=" * 75)
    for item in all_created_records:
        print(f" - {item['name']:<20} | Batch: {item['batch'][:18]:<18} | Ref: {item['ref']:<16} | Rs.{item['amount']:<3} | UTR: {item['utr']}")

    print("\n" + "=" * 75)
    print("[*] RECONCILIATION MATCHING GUIDE FOR 'live_test_statement.csv':")
    print("=" * 75)
    print("1. Open the Admin Workspace: http://localhost:5173/upi/admin/login")
    print("   Login: admin@example.com / dev_admin_password_123!")
    print("2. In 'Statement Import', upload 'live_test_statement.csv'")
    print("3. Map Columns:")
    print("   - Date         -> Col 0 (Date)")
    print("   - Description  -> Col 2 (Description)")
    print("   - Amount       -> Col 5 (Amount)")
    print("   - UTR          -> Col 6 (UTR)")
    print("   - Reference ID -> Col 7 (Remarks)    <-- Primary Matching Key")
    print("   - Direction    -> (Leave unmapped, defaults to CREDIT)")
    print("4. Navigate to your Batch Workspace (e.g. 'UPI Live Test Batch').")
    print("5. In 'Public Registrations & Payments', select the statement and click 'Match'.")
    print("6. Matched rows will immediately turn green with 'Matched'!")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
