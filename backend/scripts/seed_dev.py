"""Development-only async database seeding script.

This script populates sample courses, cohorts, and admin accounts for local development.
It must NEVER be required for production startup.
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sys
import uuid

# Ensure /app is in sys.path when script is executed directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal, engine
from app.models.admin_user import AdminUser
from app.models.course import Course
from app.models.batch import Batch


async def seed_data() -> None:
    """Seed initial development data."""
    async with AsyncSessionLocal() as session:
        print("[SEED] Checking existing development seed records...")

        # 1. Admin User
        admin_stmt = select(AdminUser).where(AdminUser.email == "admin@samagra.org")
        admin_result = await session.execute(admin_stmt)
        admin = admin_result.scalar_one_or_none()
        if not admin:
            admin = AdminUser(
                public_id=uuid.uuid4(),
                email="admin@samagra.org",
                password_hash="$2b$12$e8YkYkE7a7aRzK...dummy_dev_hash",  # dev only placeholder
                full_name="Samagra Dev Admin",
                is_active=True,
            )
            session.add(admin)
            print("[SEED] Created admin: admin@samagra.org")
        else:
            print("[SEED] Admin user already exists: admin@samagra.org")

        # 2. Sample Course: AI Masterclass
        course_stmt = select(Course).where(Course.name == "AI Masterclass")
        course_result = await session.execute(course_stmt)
        course = course_result.scalar_one_or_none()
        if not course:
            course = Course(
                public_id=uuid.uuid4(),
                name="AI Masterclass",
                description="Comprehensive practical training in applied Artificial Intelligence.",
                status="ACTIVE",
            )
            session.add(course)
            await session.flush()
            print("[SEED] Created course: AI Masterclass")
        else:
            print("[SEED] Course already exists: AI Masterclass")

        # 3. Sample Batch: August Batch (₹2000)
        batch_stmt = select(Batch).where(
            Batch.course_id == course.id,
            Batch.name == "August Batch",
        )
        batch_result = await session.execute(batch_stmt)
        batch = batch_result.scalar_one_or_none()
        if not batch:
            batch = Batch(
                public_id=uuid.uuid4(),
                course_id=course.id,
                name="August Batch",
                amount_inr=2000,
                status="ACTIVE",
                starts_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
                ends_at=datetime(2026, 8, 31, tzinfo=timezone.utc),
            )
            session.add(batch)
            print("[SEED] Created batch: August Batch (₹2000)")
        else:
            print("[SEED] Batch already exists: August Batch")

        await session.commit()
        print("[SEED] Development data seeding completed successfully.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_data())
