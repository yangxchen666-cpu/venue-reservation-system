from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models.booking import Booking
from app.models.court import Court
from app.models.user import User

TOMORROW = date.today() + timedelta(days=1)


def _payload(court_id: int, date_: date, start_time: str) -> dict:
    return {"court_id": court_id, "date": str(date_), "start_time": start_time}


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register_and_set_role(client, db_session, username: str, role: str) -> str:
    await client.post("/auth/register", json={"username": username, "password": "pass123"})
    login = await client.post("/auth/login", json={"username": username, "password": "pass123"})
    user = await db_session.scalar(select(User).where(User.username == username))
    user.role = role
    await db_session.commit()
    return login.json()["access_token"]


async def _create_custom_court(db_session, username: str, open_time: time, close_time: time) -> Court:
    owner = User(username=username, password_hash="not-used", role="venue_admin")
    db_session.add(owner)
    await db_session.flush()
    custom = Court(
        owner_id=owner.id,
        name="自定义测试馆",
        type="篮球",
        price=Decimal("50"),
        open_time=open_time,
        close_time=close_time,
        slot_minutes=60,
    )
    db_session.add(custom)
    await db_session.commit()
    await db_session.refresh(custom)
    return custom


async def test_create_booking_success(client, user_token, court):
    resp = await client.post(
        "/bookings", json=_payload(court.id, TOMORROW, "09:00:00"), headers=_auth(user_token)
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "booked"
    assert Decimal(str(data["price"])) == court.price  # 下单时价格快照
    assert data["paid"] is False
    assert data["date"] == str(TOMORROW)
    assert data["start_time"] == "09:00:00"


async def test_create_booking_court_not_found(client, user_token):
    resp = await client.post(
        "/bookings", json=_payload(99999, TOMORROW, "09:00:00"), headers=_auth(user_token)
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "球场不存在"


@pytest.mark.parametrize("role", ["venue_admin", "admin"])
async def test_create_booking_forbidden_for_privileged_roles(client, db_session, court, role):
    token = await _register_and_set_role(client, db_session, f"booker_{role}_01", role)
    resp = await client.post(
        "/bookings", json=_payload(court.id, TOMORROW, "09:00:00"), headers=_auth(token)
    )
    assert resp.status_code == 403


async def test_create_booking_requires_login(client, court):
    resp = await client.post("/bookings", json=_payload(court.id, TOMORROW, "09:00:00"))
    assert resp.status_code == 401


@pytest.mark.parametrize(
    "bad_date",
    [date.today() + timedelta(days=7), date.today() - timedelta(days=1)],
)
async def test_create_booking_date_out_of_range(client, user_token, court, bad_date):
    resp = await client.post(
        "/bookings", json=_payload(court.id, bad_date, "09:00:00"), headers=_auth(user_token)
    )
    assert resp.status_code == 409


async def test_create_booking_before_open_time(client, user_token, court):
    resp = await client.post(
        "/bookings", json=_payload(court.id, TOMORROW, "07:00:00"), headers=_auth(user_token)
    )
    assert resp.status_code == 409


async def test_create_booking_misaligned_start(client, user_token, court):
    resp = await client.post(
        "/bookings", json=_payload(court.id, TOMORROW, "09:30:00"), headers=_auth(user_token)
    )
    assert resp.status_code == 409


async def test_create_booking_exceeds_close_time(client, user_token, db_session):
    # 8:00-21:30 的球场：21:00 与 60 分钟划分对齐，但时段尾部 22:00 超出关闭时间
    custom = await _create_custom_court(db_session, "booker_owner_close01", time(8, 0), time(21, 30))
    resp = await client.post(
        "/bookings", json=_payload(custom.id, TOMORROW, "21:00:00"), headers=_auth(user_token)
    )
    assert resp.status_code == 409


async def test_create_booking_past_slot_today(client, user_token, db_session):
    # 0:00 开放的球场：当天 00:00 时段在任何运行时刻都已过
    custom = await _create_custom_court(db_session, "booker_owner_past01", time(0, 0), time(23, 0))
    resp = await client.post(
        "/bookings", json=_payload(custom.id, date.today(), "00:00:00"), headers=_auth(user_token)
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "该时段已过"


async def test_create_booking_duplicate_slot(client, user_token, court):
    payload = _payload(court.id, TOMORROW, "10:00:00")
    first = await client.post("/bookings", json=payload, headers=_auth(user_token))
    assert first.status_code == 201
    resp = await client.post("/bookings", json=payload, headers=_auth(user_token))
    assert resp.status_code == 409
    assert resp.json()["detail"] == "该时段已被预约"


async def test_create_booking_single_row_after_conflict(client, user_token, court, db_session):
    payload = _payload(court.id, TOMORROW, "11:00:00")
    assert (await client.post("/bookings", json=payload, headers=_auth(user_token))).status_code == 201
    assert (await client.post("/bookings", json=payload, headers=_auth(user_token))).status_code == 409
    count = await db_session.scalar(
        select(func.count())
        .select_from(Booking)
        .where(
            Booking.court_id == court.id,
            Booking.date == TOMORROW,
            Booking.start_time == time(11, 0),
        )
    )
    assert count == 1
