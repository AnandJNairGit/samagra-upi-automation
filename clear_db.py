"""
Database Truncation & Reset Script for Samagra UPI Automation
===============================================================
Wipes all business data (courses, batches, payment sessions, submissions,
bank transactions, statement imports, reconciliation runs & results) from PostgreSQL,
restarting auto-increment primary key identities while preserving Admin User Accounts.

Usage:
  Direct Python: python clear_db.py
  Docker Compose: docker compose exec backend python /app/clear_db.py
"""

import asyncio
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

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    db_url = os.environ["DATABASE_URL"]
    if "postgres:5432" in db_url and not os.path.exists("/.dockerenv"):
        db_url = db_url.replace("postgres:5432", "127.0.0.1:5432")

    engine = create_async_engine(db_url, echo=False)

    print("=" * 70)
    print("🔥 TRUNCATING ALL BUSINESS DATA FROM SAMAGRA UPI DATABASE")
    print("=" * 70)

    truncate_sql = text("""
        TRUNCATE TABLE 
            reconciliation_results,
            reconciliation_runs,
            payment_submissions,
            payment_sessions,
            bank_transactions,
            statement_imports,
            batches,
            courses
        RESTART IDENTITY CASCADE;
    """)

    async with engine.begin() as conn:
        await conn.execute(truncate_sql)

    # Clean demo CSV files if present
    demo_files = ["demo_test_statement.csv", "demo_reconciliation_statement.csv"]
    for fname in demo_files:
        for p in [os.path.join(BASE_DIR, fname), f"/tmp/{fname}"]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                    print(f"Removed demo file: {p}")
                except Exception:
                    pass

    print("\n✅ Successfully truncated all database tables:")
    print("   • Courses")
    print("   • Batches")
    print("   • Payment Sessions")
    print("   • Payment Submissions")
    print("   • Bank Transactions")
    print("   • Statement Imports")
    print("   • Reconciliation Runs")
    print("   • Reconciliation Results")
    print("\n(Admin user accounts and system configuration remain intact).")

    print("\n" + "=" * 70)
    print("✨ DATABASE RESET COMPLETE!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
