"""Development seed script to initialize a test admin user.

Usage:
  DEV_ADMIN_PASSWORD=my_secure_dev_pwd python scripts/seed_dev.py
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path

# Ensure application root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.hashing import hash_password
from app.core.config import settings
from app.core.database import async_session_factory
from app.models.admin_user import AdminUser


async def seed_dev_admin() -> None:
    """Seed initial development administrator account."""
    if settings.is_production:
        print("[ERROR] Cannot run development seed script in production environment!", file=sys.stderr)
        sys.exit(1)

    dev_password = os.environ.get("DEV_ADMIN_PASSWORD") or settings.DEV_ADMIN_PASSWORD
    if not dev_password or not dev_password.strip():
        print(
            "[ERROR] DEV_ADMIN_PASSWORD is required in environment to seed development admin.\n"
            "Example: DEV_ADMIN_PASSWORD=my_dev_password_123 python scripts/seed_dev.py",
            file=sys.stderr,
        )
        sys.exit(1)

    email = "admin@example.com"
    full_name = "Development Admin"

    print(f"[*] Seeding development admin user [{email}]...")
    hashed_pwd = hash_password(dev_password.strip())

    async with async_session_factory() as session:  # type: AsyncSession
        stmt = select(AdminUser).where(AdminUser.email == email)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            print(f"[*] Updating existing admin user [{existing.public_id}] with new development password...")
            existing.password_hash = hashed_pwd
            existing.is_active = True
            existing.full_name = full_name
            await session.commit()
            print("[+] Development admin successfully updated.")
        else:
            new_admin = AdminUser(
                public_id=uuid.uuid4(),
                email=email,
                password_hash=hashed_pwd,
                full_name=full_name,
                is_active=True,
            )
            session.add(new_admin)
            await session.commit()
            print(f"[+] Development admin [{new_admin.public_id}] created successfully.")


if __name__ == "__main__":
    asyncio.run(seed_dev_admin())
