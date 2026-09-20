from datetime import date, time, timedelta

import pytest
from sqlalchemy import func, select

from app.models.booking import Booking
from app.models.user import User

TOMORROW = date.today() + timedelta(days=1)
DAY_AFTER = date.today() + timedelta(days=2)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _book(client, token: str, court_id: int, date_: date, start_time: str) -> dict:
    resp = await client.post(
        "/bookings",
        json={"court_id": court_id, "date": str(date_), "start_time": start_time},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    return resp.json()


async def _new_user_token(client, username: str) -> str:
    await client.post("/auth/register", json={"username": username, "password": "pass123"})
    login = await client.post("/auth/login", json={"username": username, "password": "pass123"})
    return login.json()["access_token"]


async def _user_id(db_session, username: str) -> int:
    user = await db_session.scalar(select(User).where(User.username == username))
    return user.id


async def _insert_booking(
    db_session, user_id: int, court_id: int, date_: date, start_time: time, status: str = "booked"
) -> int:
    booking = Booking(
        user_id=user_id, court_id=court_id, date=date_, start_time=start_time, status=status
    )
    db_session.add(booking)
    await db_session.commit()
    await db_session.refresh(booking)
    return booking.id


async def test_my_bookings_returns_only_mine_sorted(client, user_token, court):
    # 本人 3 条：D1 11:00、D2 09:00、D2 10:00（跨日期造数以验证双键排序）
    await _book(client, user_token, court.id, TOMORROW, "11:00:00")
    await _book(client, user_token, court.id, DAY_AFTER, "09:00:00")
    await _book(client, user_token, court.id, DAY_AFTER, "10:00:00")
    # 他人 1 条：不应出现在我的列表
    other_token = await _new_user_token(client, "other_user01")
    await _book(client, other_token, court.id, TOMORROW, "10:00:00")

    resp = await client.get("/bookings/my", headers=_auth(user_token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    assert [(b["date"], b["start_time"]) for b in data] == [
        (str(DAY_AFTER), "10:00:00"),
        (str(DAY_AFTER), "09:00:00"),
        (str(TOMORROW), "11:00:00"),
    ]
    for booking in data:
        assert booking["court_name"] == "测试羽毛球馆"


async def test_my_bookings_requires_login(client):
    assert (await client.get("/bookings/my")).status_code == 401


async def test_cancel_own_booking(client, user_token, court, db_session):
    booking = await _book(client, user_token, court.id, TOMORROW, "09:00:00")
    resp = await client.delete(f"/bookings/{booking['id']}", headers=_auth(user_token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"
    # 软取消：记录保留，仅状态变更
    row = await db_session.get(Booking, booking["id"])
    assert row is not None
    assert row.status == "cancelled"
    count = await db_session.scalar(
        select(func.count()).select_from(Booking).where(Booking.id == booking["id"])
    )
    assert count == 1


async def test_cancel_others_booking_forbidden(client, user_token, court):
    other_token = await _new_user_token(client, "other_user02")
    booking = await _book(client, other_token, court.id, TOMORROW, "10:00:00")
    resp = await client.delete(f"/bookings/{booking['id']}", headers=_auth(user_token))
    assert resp.status_code == 403


async def test_cancel_booking_not_found(client, user_token):
    resp = await client.delete("/bookings/99999", headers=_auth(user_token))
    assert resp.status_code == 404
    assert resp.json()["detail"] == "预定不存在"


async def test_cancel_started_booking_conflict(client, user_token, court, db_session):
    user_id = await _user_id(db_session, "fixture_user01")
    # 当天 00:00 的预定在任何运行时刻均已开始（直插绕过下单校验）
    booking_id = await _insert_booking(db_session, user_id, court.id, date.today(), time(0, 0))
    resp = await client.delete(f"/bookings/{booking_id}", headers=_auth(user_token))
    assert resp.status_code == 409
    assert resp.json()["detail"] == "时段已开始，无法取消"


@pytest.mark.parametrize("status", ["checked_in", "cancelled"])
async def test_cancel_invalid_status_conflict(client, user_token, court, db_session, status):
    user_id = await _user_id(db_session, "fixture_user01")
    booking_id = await _insert_booking(db_session, user_id, court.id, TOMORROW, time(9, 0), status=status)
    resp = await client.delete(f"/bookings/{booking_id}", headers=_auth(user_token))
    assert resp.status_code == 409


async def test_cancel_requires_login(client):
    resp = await client.delete("/bookings/99999")
    assert resp.status_code == 401
