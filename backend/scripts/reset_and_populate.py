"""Reset Database and Populate Test Data with Corresponding Statement Files.

This script:
1. Clears all operational data (BankTransactions, StatementImports, PaymentSubmissions,
   PaymentSessions, Batches, Courses, AdminSessions).
2. Keeps AdminUser accounts intact (admin@samagra.org & admin@example.com).
3. Seeds realistic Courses, Batches, Payment Sessions, and Submissions.
4. Generates matching test statement files (`test_bank_statement.xlsx` and `test_bank_statement.csv`)
   directly in the project root directory.

Usage:
  docker compose exec backend python scripts/reset_and_populate.py
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Ensure backend path on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select
from app.auth.hashing import hash_password
from app.core.database import async_session_factory
from app.models.admin_user import AdminUser
from app.models.admin_session import AdminSession
from app.models.course import Course
from app.models.batch import Batch
from app.models.payment_session import PaymentSession
from app.models.payment_submission import PaymentSubmission
from app.models.statement_import import StatementImport
from app.models.bank_transaction import BankTransaction
import openpyxl


async def reset_and_populate():
    print("[*] Clearing database tables (except AdminUsers)...")

    async with async_session_factory() as session:
        # Clear child tables first
        await session.execute(delete(BankTransaction))
        await session.execute(delete(StatementImport))
        await session.execute(delete(PaymentSubmission))
        await session.execute(delete(PaymentSession))
        await session.execute(delete(Batch))
        await session.execute(delete(Course))
        await session.execute(delete(AdminSession))
        await session.commit()
        print("[+] Operational database tables cleared successfully.")

        # Ensure admin user exists
        admin_email = "admin@samagra.org"
        admin_res = await session.execute(select(AdminUser).where(AdminUser.email == admin_email))
        admin = admin_res.scalar_one_or_none()

        if not admin:
            admin = AdminUser(
                public_id=uuid.uuid4(),
                email=admin_email,
                password_hash=hash_password("dev_admin_password_123!"),
                full_name="Samagra Admin",
                is_active=True,
            )
            session.add(admin)
            await session.commit()
            await session.refresh(admin)

        # Ensure admin@example.com also exists
        ex_email = "admin@example.com"
        ex_res = await session.execute(select(AdminUser).where(AdminUser.email == ex_email))
        ex_admin = ex_res.scalar_one_or_none()
        if not ex_admin:
            ex_admin = AdminUser(
                public_id=uuid.uuid4(),
                email=ex_email,
                password_hash=hash_password("dev_admin_password_123!"),
                full_name="Development Admin",
                is_active=True,
            )
            session.add(ex_admin)
            await session.commit()

        # 1. Create Courses
        print("[*] Creating test Courses...")
        course1 = Course(
            public_id=uuid.uuid4(),
            name="Full Stack Web Development",
            description="Comprehensive MERN & Python Web Development Course",
            status="ACTIVE",
        )
        course2 = Course(
            public_id=uuid.uuid4(),
            name="Data Science & AI Bootcamp",
            description="Hands-on Machine Learning, AI & Data Engineering",
            status="ACTIVE",
        )
        session.add_all([course1, course2])
        await session.commit()
        await session.refresh(course1)
        await session.refresh(course2)

        # 2. Create Batches
        print("[*] Creating test Batches...")
        batch1 = Batch(
            public_id=uuid.uuid4(),
            course_id=course1.id,
            name="August 2026 Morning Batch",
            amount_inr=15000,
            status="ACTIVE",
        )
        batch2 = Batch(
            public_id=uuid.uuid4(),
            course_id=course2.id,
            name="Weekend Fast Track Batch",
            amount_inr=25000,
            status="ACTIVE",
        )
        session.add_all([batch1, batch2])
        await session.commit()
        await session.refresh(batch1)
        await session.refresh(batch2)

        # 3. Create Payment Sessions & Submissions
        print("[*] Creating test Payment Sessions & Submissions...")

        participants = [
            {
                "name": "Rahul Sharma",
                "phone": "9876543210",
                "email": "rahul.sharma@example.com",
                "course": course1,
                "batch": batch1,
                "amount": 15000,
                "ref": "REF-FSWD-1001",
                "utr": "423456789012",
                "status": "SUBMITTED",
            },
            {
                "name": "Priya Patel",
                "phone": "9876543211",
                "email": "priya.patel@example.com",
                "course": course1,
                "batch": batch1,
                "amount": 15000,
                "ref": "REF-FSWD-1002",
                "utr": "423456789013",
                "status": "SUBMITTED",
            },
            {
                "name": "Anish Verma",
                "phone": "9876543212",
                "email": "anish.verma@example.com",
                "course": course1,
                "batch": batch1,
                "amount": 15000,
                "ref": "REF-FSWD-1003",
                "utr": "423456789014",
                "status": "SUBMITTED",
            },
            {
                "name": "Sneha Reddy",
                "phone": "9876543213",
                "email": "sneha.reddy@example.com",
                "course": course2,
                "batch": batch2,
                "amount": 25000,
                "ref": "REF-DSAI-2001",
                "utr": "423456789015",
                "status": "SUBMITTED",
            },
            {
                "name": "Vikram Singh",
                "phone": "9876543214",
                "email": "vikram.singh@example.com",
                "course": course2,
                "batch": batch2,
                "amount": 25000,
                "ref": "REF-DSAI-2002",
                "utr": None,
                "status": "PENDING",
            },
        ]

        for p in participants:
            ps = PaymentSession(
                public_id=uuid.uuid4(),
                full_name=p["name"],
                phone=p["phone"],
                email=p["email"],
                course_id=p["course"].id,
                batch_id=p["batch"].id,
                course_name_snapshot=p["course"].name,
                batch_name_snapshot=p["batch"].name,
                amount_inr=p["amount"],
                reference_id=p["ref"],
                upi_id_snapshot="samagra@upi",
                payee_name_snapshot="Samagra Educational Trust",
                upi_uri=f"upi://pay?pa=samagra@upi&pn=Samagra&am={p['amount']}&tr={p['ref']}&cu=INR",
                status=p["status"],
            )
            session.add(ps)
            await session.commit()
            await session.refresh(ps)

            if p["utr"]:
                sub = PaymentSubmission(
                    public_id=uuid.uuid4(),
                    payment_session_id=ps.id,
                    utr=p["utr"],
                    status="SUBMITTED",
                    is_current=True,
                )
                session.add(sub)
                await session.commit()

        print("[+] Successfully seeded Courses, Batches, Payment Sessions, and Submissions.")

    # 4. Generate matching dummy Excel & CSV files in root directory
    generate_dummy_files()


def generate_dummy_files():
    root_dir = Path("/tmp")

    excel_path = root_dir / "test_bank_statement.xlsx"
    csv_path = root_dir / "test_bank_statement.csv"

    headers = [
        "Txn Date & Time",
        "Transaction Remarks / Description",
        "Amount (INR)",
        "Credit / Debit",
        "Bank UTR / RRN",
        "Payer Name",
    ]

    rows = [
        [
            "15/08/2026 10:32:15",
            "UPI/CR/423456789012/REF-FSWD-1001/Rahul Sharma",
            15000,
            "CREDIT",
            "423456789012",
            "Rahul Sharma",
        ],
        [
            "15/08/2026 11:17:40",
            "UPI-CR-423456789013-REF-FSWD-1002",
            15000,
            "CREDIT",
            "423456789013",
            "Priya Patel",
        ],
        [
            "16/08/2026 09:48:02",
            "Payment for REF-FSWD-1003 via PhonePe",
            15000,
            "CREDIT",
            "423456789014",
            "Anish Verma",
        ],
        [
            "16/08/2026 14:22:10",
            "Ref REF-DSAI-2001 UTR 423456789015",
            25000,
            "CREDIT",
            "423456789015",
            "Sneha Reddy",
        ],
        [
            "16/08/2026 16:05:00",
            "UPI Transfer from Unmatched User REF-UNMATCH-999",
            5000,
            "CREDIT",
            "423456789999",
            "Unknown Payer",
        ],
    ]

    # Create Excel Workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Passbook Payment History"

    ws.append(headers)
    for row in rows:
        ws.append(row)

    wb.save(str(excel_path))
    print(f"[+] Created Excel statement file at: {excel_path}")

    # Create CSV file
    import csv

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    print(f"[+] Created CSV statement file at: {csv_path}")


if __name__ == "__main__":
    asyncio.run(reset_and_populate())
