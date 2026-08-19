"""
Seed Manual Test Data Script for Samagra UPI Automation
=========================================================
This script generates 3 Courses with corresponding Batches and Payment Registrations in PostgreSQL,
and outputs a test bank statement CSV file (demo_test_statement.csv) containing both MATCHED and NON-MATCHING
bank transactions for thorough manual testing in the Admin Workspace.

Usage:
  Direct Python: python seed_manual_test_data.py
  Docker Compose: docker compose exec backend python /app/scripts/seed_manual_test_data.py
"""

import asyncio
import csv
import os
import sys

# Add backend directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if os.path.exists(BACKEND_DIR) and BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Database connection fallback for running outside container
if "DATABASE_URL" not in os.environ:
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://app_user:change_me_to_a_secure_password@127.0.0.1:5432/training_payments"

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select, delete
from app.models.course import Course
from app.models.batch import Batch
from app.models.payment_session import PaymentSession
from app.models.payment_submission import PaymentSubmission
from app.models.statement_import import StatementImport
from app.models.bank_transaction import BankTransaction
from app.models.reconciliation_run import ReconciliationRun
from app.models.reconciliation_result import ReconciliationResult

SEED_TAG = "[MANUAL_TEST_SEED]"
SEED_COURSES = [
    "Full Stack Web Development",
    "Data Science & Artificial Intelligence",
    "Cloud Computing & DevOps",
]

async def main():
    db_url = os.environ["DATABASE_URL"]
    if "postgres:5432" in db_url and not os.path.exists("/.dockerenv"):
        db_url = db_url.replace("postgres:5432", "127.0.0.1:5432")

    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    print("=" * 70)
    print("🌱 SEEDING MANUAL TEST DATA FOR SAMAGRA UPI AUTOMATION")
    print("=" * 70)

    async with async_session() as db:
        # First, auto-clean any existing seed records to maintain idempotency
        stmt_c = select(Course).where(Course.name.in_(SEED_COURSES))
        res_c = await db.execute(stmt_c)
        existing_courses = list(res_c.scalars().all())
        if existing_courses:
            c_ids = [c.id for c in existing_courses]
            stmt_b = select(Batch).where(Batch.course_id.in_(c_ids))
            res_b = await db.execute(stmt_b)
            b_ids = [b.id for b in res_b.scalars().all()]

            stmt_ps = select(PaymentSession).where(PaymentSession.course_id.in_(c_ids))
            res_ps = await db.execute(stmt_ps)
            ps_ids = [ps.id for ps in res_ps.scalars().all()]

            if ps_ids:
                await db.execute(delete(ReconciliationResult).where(ReconciliationResult.payment_session_id.in_(ps_ids)))
            if b_ids:
                await db.execute(delete(ReconciliationRun).where(ReconciliationRun.batch_id.in_(b_ids)))
            if ps_ids:
                await db.execute(delete(PaymentSubmission).where(PaymentSubmission.payment_session_id.in_(ps_ids)))
                await db.execute(delete(PaymentSession).where(PaymentSession.id.in_(ps_ids)))
            if b_ids:
                await db.execute(delete(Batch).where(Batch.id.in_(b_ids)))
            await db.execute(delete(Course).where(Course.id.in_(c_ids)))
            await db.commit()

        # 1. Create Courses
        print("\n1. Creating 3 Sample Courses...")
        course1 = Course(
            name="Full Stack Web Development",
            description=f"{SEED_TAG} Master React, FastAPI & PostgreSQL",
            status="ACTIVE",
        )
        course2 = Course(
            name="Data Science & Artificial Intelligence",
            description=f"{SEED_TAG} Machine Learning, Deep Learning & Python",
            status="ACTIVE",
        )
        course3 = Course(
            name="Cloud Computing & DevOps",
            description=f"{SEED_TAG} Docker, Kubernetes, CI/CD & AWS",
            status="ACTIVE",
        )
        db.add_all([course1, course2, course3])
        await db.flush()

        # 2. Create Batches
        print("2. Creating 3 Corresponding Batches...")
        batch1 = Batch(
            course_id=course1.id,
            name="FSWD Morning Batch (Jan 2026)",
            amount_inr=5000,
            status="ACTIVE",
        )
        batch2 = Batch(
            course_id=course2.id,
            name="DSAI Evening Batch (Feb 2026)",
            amount_inr=10000,
            status="ACTIVE",
        )
        batch3 = Batch(
            course_id=course3.id,
            name="DevOps Weekend Batch (Mar 2026)",
            amount_inr=7500,
            status="ACTIVE",
        )
        db.add_all([batch1, batch2, batch3])
        await db.flush()

        # 3. Create Public Registrations & Payments
        print("3. Creating Sample Participant Payment Sessions & Submissions...")
        upi_id = "samagra.edu@okicici"
        payee_name = "Samagra Educational Foundation"
        upi_uri = "upi://pay?pa=samagra.edu@okicici&pn=Samagra%20Educational%20Foundation"

        sessions_data = [
            {"batch": batch1, "course": course1, "name": "Rahul Sharma", "phone": "9876543210", "email": "rahul.sharma@example.com", "ref": "REF-FSWD-101", "utr": "305412984712"},
            {"batch": batch1, "course": course1, "name": "Ananya Patel", "phone": "9876543211", "email": "ananya.p@example.com", "ref": "REF-FSWD-102", "utr": "305412984713"},
            {"batch": batch2, "course": course2, "name": "Vikram Singh", "phone": "9876543212", "email": "vikram.s@example.com", "ref": "REF-DSAI-201", "utr": "419283746501"},
            {"batch": batch2, "course": course2, "name": "Priya Nair", "phone": "9876543213", "email": "priya.nair@example.com", "ref": "REF-DSAI-202", "utr": "419283746502"},
            {"batch": batch3, "course": course3, "name": "Suresh Kumar", "phone": "9876543214", "email": "suresh.k@example.com", "ref": "REF-DEVOPS-301", "utr": "512398475601"},
            {"batch": batch3, "course": course3, "name": "Meera Joshi", "phone": "9876543215", "email": "meera.j@example.com", "ref": "REF-DEVOPS-302", "utr": "512398475602"},
        ]

        created_sessions = []
        for d in sessions_data:
            ps = PaymentSession(
                full_name=d["name"],
                phone=d["phone"],
                email=d["email"],
                course_id=d["course"].id,
                batch_id=d["batch"].id,
                course_name_snapshot=d["course"].name,
                batch_name_snapshot=d["batch"].name,
                amount_inr=d["batch"].amount_inr,
                reference_id=d["ref"],
                upi_id_snapshot=upi_id,
                payee_name_snapshot=payee_name,
                upi_uri=upi_uri,
                status="SUBMITTED",
            )
            db.add(ps)
            await db.flush()

            sub = PaymentSubmission(
                payment_session_id=ps.id,
                utr=d["utr"],
                status="SUBMITTED",
                is_current=True,
            )
            db.add(sub)
            created_sessions.append((ps, sub, d["batch"]))

        await db.commit()

        print("\n✅ Successfully seeded database records!")
        print("\nCourses Created:")
        print(f"  • {course1.name} (Public ID: {course1.public_id})")
        print(f"  • {course2.name} (Public ID: {course2.public_id})")
        print(f"  • {course3.name} (Public ID: {course3.public_id})")

        print("\nBatches Created:")
        print(f"  • {batch1.name} | Fee: ₹{batch1.amount_inr} | Public ID: {batch1.public_id}")
        print(f"  • {batch2.name} | Fee: ₹{batch2.amount_inr} | Public ID: {batch2.public_id}")
        print(f"  • {batch3.name} | Fee: ₹{batch3.amount_inr} | Public ID: {batch3.public_id}")

        print("\nRegistered Participants:")
        for ps, sub, b in created_sessions:
            print(f"  • {ps.full_name:<15} | Batch: {b.name[:20]:<20} | Ref: {ps.reference_id} | Fee: ₹{ps.amount_inr} | UTR: {sub.utr}")

    # Write CSV to root directory or fallback to /tmp
    # Column layout: Date(0), Description(1), Ref No(2), Direction(3), Amount(4), UTR(5)
    # Direction column uses CREDIT/DEBIT so the import UI can map it correctly.
    csv_rows = [
        ["Date", "Description", "Ref No", "Direction", "Amount", "UTR"],
        ["18/08/2026", "UPI/CR/Rahul Sharma/REF-FSWD-101",      "REF-FSWD-101",   "CREDIT", "5000",  "305412984712"],  # MATCHED
        ["18/08/2026", "UPI/CR/Vikram Singh/REF-DSAI-201",      "REF-DSAI-201",   "CREDIT", "10000", "419283746501"],  # MATCHED
        ["18/08/2026", "UPI/CR/Suresh Kumar/REF-DEVOPS-301",    "REF-DEVOPS-301", "CREDIT", "7500",  "512398475601"],  # MATCHED
        ["18/08/2026", "UPI/CR/Ananya Patel/REF-FSWD-102",      "REF-FSWD-102",   "CREDIT", "4500",  "305412984713"],  # AMOUNT MISMATCH (paid 4500, expected 5000)
        ["18/08/2026", "UPI/CR/Priya Nair/REF-DSAI-202",        "REF-DSAI-202",   "CREDIT", "10000", "999999999999"],  # UTR MISMATCH
        ["18/08/2026", "UPI/CR/Unknown Transfer",               "REF-UNKNOWN-999","CREDIT", "5000",  "777777777777"],  # UNKNOWN REFERENCE
        ["18/08/2026", "Bank Cash Deposit",                     "",               "CREDIT", "2000",  "888888888888"],  # NO REFERENCE
        ["18/08/2026", "Bank Monthly Service Fee",              "FEE-AUG-2026",   "DEBIT",  "150",   "111111111111"],  # NON-CREDIT (Debit)
        ["18/08/2026", "UPI/CR/Suresh Kumar Duplicate",        "REF-DEVOPS-301", "CREDIT", "7500",  "512398475601"],  # DUPLICATE TRANSACTION
    ]

    # Determine CSV write path
    # Inside Docker: /app is a read-only mount, so write to /tmp
    # On host: write to project root for easy access
    in_docker = os.path.exists("/.dockerenv")
    if in_docker:
        target_csv = "/tmp/demo_test_statement.csv"
    else:
        target_csv = os.path.join(BASE_DIR, "demo_test_statement.csv")

    with open(target_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(csv_rows)
    print(f"\n4. Created Bank Statement CSV file at: {target_csv}")
    if in_docker:
        print("   ⚠️  Running in Docker — copy the file to your host with:")
        print("       docker compose cp backend:/tmp/demo_test_statement.csv ./demo_test_statement.csv")

    print("\n" + "=" * 70)
    print("🚀 MANUAL TESTING INSTRUCTIONS:")
    print("=" * 70)
    print("1. Open the Admin Workspace in your browser:")
    print("   http://localhost:5173/upi/admin/login")
    print("   Login: admin@example.com / dev_admin_password_123!")
    print("2. Navigate to Batches and select one of the newly created batches")
    print("   (e.g., 'FSWD Morning Batch (Jan 2026)' or 'DSAI Evening Batch').")
    print("3. In the Bank Transactions tab or Statement Upload modal:")
    print(f"   Upload the generated statement file: {target_csv}")
    print("4. Column Mapping Guide (0-indexed):")
    print("   Date      → column 0 (Date)")
    print("   Ref No    → column 2 (Ref No)       ← REQUIRED")
    print("   Direction → column 3 (Direction)    ← Map to 'Direction' field")
    print("   Amount    → column 4 (Amount)       ← REQUIRED")
    print("   UTR       → column 5 (UTR)          ← Map to 'UTR' field")
    print("5. In the top right of the 'Public Registrations & Payments' table:")
    print("   Select the imported statement file from the dropdown and click 'Match'.")
    print("6. Watch matching rows automatically update to green `✓ Matched`!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
