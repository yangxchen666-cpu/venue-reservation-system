import asyncio
from datetime import date, timedelta

from sqlalchemy import func, select

from app.models.booking import Booking

TOMORROW = date.today() + timedelta(days=1)


async def test_concurrent_same_slot_only_one_succeeds(client, user_token, court, db_session):
    payload = {"court_id": court.id, "date": str(TOMORROW), "start_time": "09:00:00"}
    headers = {"Authorization": f"Bearer {user_token}"}

    async def book():
        return await client.post("/bookings", json=payload, headers=headers)

    r1, r2 = await asyncio.gather(book(), book())
    assert sorted([r1.status_code, r2.status_code]) == [201, 409]

    # 数据库层面该时段恒为 1 条记录（唯一约束硬保证）
    count = await db_session.scalar(
        select(func.count()).select_from(Booking).where(
            Booking.court_id == court.id,
            Booking.date == TOMORROW,
        )
    )
    assert count == 1
