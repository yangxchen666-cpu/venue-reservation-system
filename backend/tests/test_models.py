from datetime import date, time

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.booking import Booking
from app.models.court import Court
from app.models.user import User


async def _create_user(db, username: str) -> User:
    user = User(username=username, password_hash="x")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _create_court(db, owner: User) -> Court:
    court = Court(owner_id=owner.id, name="测试球场", type="羽毛球", price=50,
                  open_time=time(9, 0), close_time=time(22, 0), slot_minutes=60)
    db.add(court)
    await db.commit()
    await db.refresh(court)
    return court


@pytest.mark.asyncio
async def test_user_default_role(db_session):
    user = await _create_user(db_session, "alice")
    assert user.role == "user"


@pytest.mark.asyncio
async def test_booking_unique_constraint(db_session):
    owner = await _create_user(db_session, "owner1")
    court = await _create_court(db_session, owner)
    user = await _create_user(db_session, "bob")
    d, t = date(2026, 9, 26), time(9, 0)

    db_session.add(Booking(user_id=user.id, court_id=court.id, date=d, start_time=t))
    await db_session.commit()

    db_session.add(Booking(user_id=user.id, court_id=court.id, date=d, start_time=t))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_court_cross_day_only_enforced_in_app_layer(db_session):
    # 跨日营业（open_time >= close_time）规则由应用层负责（任务 10 的 POST /venue-admin/courts 422），
    # DB 层不设 CHECK 约束：可正常插入，仅应用层拒绝。
    owner = await _create_user(db_session, "owner2")
    court = Court(owner_id=owner.id, name="跨日球场", type="篮球", price=30,
                  open_time=time(22, 0), close_time=time(6, 0), slot_minutes=60)
    db_session.add(court)
    await db_session.commit()
    await db_session.refresh(court)
    assert court.open_time >= court.close_time
