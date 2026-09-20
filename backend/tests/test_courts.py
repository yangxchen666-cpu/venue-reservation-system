from datetime import date, time
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.booking import Booking
from app.models.court import Court
from app.models.user import User
from app.schemas.courts import CourtCreate

PRICE_MIN = "50"
PRICE_MAX = "100"


async def _seed_user(db_session, username: str, role: str = "venue_admin") -> int:
    user = User(username=username, password_hash="not-used", role=role)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user.id


async def _create_court(
    db_session,
    owner_id: int,
    name: str,
    type_: str,
    price: str,
    open_time: time = time(8, 0),
    close_time: time = time(22, 0),
    slot_minutes: int = 60,
) -> Court:
    court = Court(
        owner_id=owner_id,
        name=name,
        type=type_,
        price=Decimal(price),
        open_time=open_time,
        close_time=close_time,
        slot_minutes=slot_minutes,
    )
    db_session.add(court)
    await db_session.commit()
    await db_session.refresh(court)
    return court


async def test_list_courts_empty(client):
    resp = await client.get("/courts")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_courts_returns_all_fields(client, db_session):
    owner_id = await _seed_user(db_session, "owner_list01")
    await _create_court(db_session, owner_id, "阳光羽毛球馆", "羽毛球", "80")
    await _create_court(db_session, owner_id, "奥体篮球场", "篮球", "120")
    resp = await client.get("/courts")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["id"] < data[1]["id"]  # ORDER BY id
    for court in data:
        for field in ["id", "name", "type", "price", "open_time", "close_time", "slot_minutes"]:
            assert field in court
    assert [c["name"] for c in data] == ["阳光羽毛球馆", "奥体篮球场"]


async def test_list_courts_filter_by_type(client, db_session):
    owner_id = await _seed_user(db_session, "owner_type01")
    await _create_court(db_session, owner_id, "阳光羽毛球馆", "羽毛球", "80")
    await _create_court(db_session, owner_id, "奥体篮球场", "篮球", "120")
    resp = await client.get("/courts", params={"type": "篮球"})
    assert resp.status_code == 200
    assert [c["name"] for c in resp.json()] == ["奥体篮球场"]


async def test_list_courts_filter_by_price_range(client, db_session):
    owner_id = await _seed_user(db_session, "owner_price01")
    await _create_court(db_session, owner_id, "低价场", "羽毛球", "30")
    await _create_court(db_session, owner_id, "中价场", "篮球", "80")
    await _create_court(db_session, owner_id, "高价场", "网球", "150")
    resp = await client.get("/courts", params={"price_min": PRICE_MIN, "price_max": PRICE_MAX})
    assert resp.status_code == 200
    assert [c["name"] for c in resp.json()] == ["中价场"]


async def test_get_court_detail(client, db_session):
    owner_id = await _seed_user(db_session, "owner_detail01")
    court = await _create_court(db_session, owner_id, "阳光羽毛球馆", "羽毛球", "80")
    resp = await client.get(f"/courts/{court.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "阳光羽毛球馆"
    assert data["slot_minutes"] == 60
    assert data["open_time"] == "08:00:00"


async def test_get_court_not_found(client):
    resp = await client.get("/courts/99999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "球场不存在"


async def test_court_create_rejects_unknown_type():
    # 挂到创建端点后 FastAPI 会将 ValidationError 转成 422
    with pytest.raises(ValidationError):
        CourtCreate(
            name="测试场",
            type="乒乓球",
            price=Decimal("50"),
            open_time=time(8, 0),
            close_time=time(22, 0),
        )


async def test_court_create_accepts_valid_type():
    court = CourtCreate(
        name="测试场",
        type="足球",
        price=Decimal("50"),
        open_time=time(8, 0),
        close_time=time(22, 0),
    )
    assert court.type == "足球"


async def test_booked_slots_empty(client, db_session):
    owner_id = await _seed_user(db_session, "owner_slot01")
    court = await _create_court(db_session, owner_id, "阳光羽毛球馆", "羽毛球", "80")
    resp = await client.get(f"/courts/{court.id}/booked-slots", params={"date": "2026-09-25"})
    assert resp.status_code == 200
    assert resp.json() == []


async def test_booked_slots_returns_booked_start_times(client, db_session):
    owner_id = await _seed_user(db_session, "owner_slot02")
    court = await _create_court(db_session, owner_id, "阳光羽毛球馆", "羽毛球", "80")
    user_id = await _seed_user(db_session, "booking_user01", role="user")
    db_session.add(
        Booking(user_id=user_id, court_id=court.id, date=date(2026, 9, 25), start_time=time(9, 0))
    )
    await db_session.commit()
    resp = await client.get(f"/courts/{court.id}/booked-slots", params={"date": "2026-09-25"})
    assert resp.status_code == 200
    assert resp.json() == ["09:00:00"]


async def test_booked_slots_requires_date(client):
    resp = await client.get("/courts/1/booked-slots")
    assert resp.status_code == 422


async def test_booked_slots_excludes_cancelled(client, db_session):
    owner_id = await _seed_user(db_session, "owner_slot03")
    court = await _create_court(db_session, owner_id, "阳光羽毛球馆", "羽毛球", "80")
    user_id = await _seed_user(db_session, "booking_user02", role="user")
    db_session.add(
        Booking(
            user_id=user_id,
            court_id=court.id,
            date=date(2026, 9, 25),
            start_time=time(9, 0),
            status="cancelled",
        )
    )
    await db_session.commit()
    resp = await client.get(f"/courts/{court.id}/booked-slots", params={"date": "2026-09-25"})
    assert resp.json() == []


async def test_booked_slots_court_not_found(client):
    resp = await client.get("/courts/99999/booked-slots", params={"date": "2026-09-25"})
    assert resp.status_code == 404
