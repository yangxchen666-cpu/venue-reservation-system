import asyncio

from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models.user import User
from app.security import hash_password


async def seed_admin() -> None:
    async with SessionLocal() as db:
        existing = await db.scalar(select(User).where(User.username == settings.seed_admin_username))
        if existing:
            print(f"seed skipped: {settings.seed_admin_username} already exists")
            return
        db.add(User(username=settings.seed_admin_username,
                    password_hash=hash_password(settings.seed_admin_password),
                    role="admin"))
        await db.commit()
        print(f"seed created admin: {settings.seed_admin_username}")


if __name__ == "__main__":
    asyncio.run(seed_admin())
