from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models.booking import Booking
from app.models.court import Court
from app.models.user import User

TOMORROW = date.today() + timedelta(days=1)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _user_id(db_session, username: str) -> int:
    user = await db_session.scalar(select(User).where(User.username == username))
    return user.id


async def _insert_user(db_session, username: str, role: str = "user") -> int:
    user = User(username=username, password_hash="not-used", role=role)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user.id


async def _insert_court(
    db_session,
    owner_id: int,
    name: str,
    type_: str = "羽毛球",
) -> Court:
    court = Court(
        owner_id=owner_id,
        name=name,
        type=type_,
        price=Decimal("80"),
        open_time=time(8, 0),
        close_time=time(22, 0),
        slot_minutes=60,
    )
    db_session.add(court)
    await db_session.commit()
    await db_session.refresh(court)
    return court


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


def _court_payload(owner_id: int, **overrides) -> dict:
    payload = {
        "owner_id": owner_id,
        "name": "全局新建馆",
        "type": "羽毛球",
        "price": "80",
        "open_time": "08:00:00",
        "close_time": "22:00:00",
        "slot_minutes": 60,
    }
    payload.update(overrides)
    return payload


async def test_list_all_courts(client, admin_token, db_session):
    owner_a = await _insert_user(db_session, "court_owner_a", role="venue_admin")
    owner_b = await _insert_user(db_session, "court_owner_b", role="venue_admin")
    await _insert_court(db_session, owner_a, "甲馆")
    await _insert_court(db_session, owner_b, "乙馆", type_="篮球")

    resp = await client.get("/admin/courts", headers=_auth(admin_token))
    assert resp.status_code == 200
    assert [c["name"] for c in resp.json()] == ["甲馆", "乙馆"]


async def test_create_court_with_owner(client, admin_token, db_session):
    owner = await _insert_user(db_session, "court_owner_c", role="venue_admin")
    resp = await client.post(
        "/admin/courts", json=_court_payload(owner), headers=_auth(admin_token)
    )
    assert resp.status_code == 201
    data = resp.json()
    row = await db_session.get(Court, data["id"])
    assert row is not None
    assert row.owner_id == owner


async def test_create_court_owner_must_be_venue_admin(client, admin_token, db_session):
    plain_user = await _insert_user(db_session, "court_owner_plain", role="user")
    resp = await client.post(
        "/admin/courts", json=_court_payload(plain_user), headers=_auth(admin_token)
    )
    assert resp.status_code == 422


async def test_create_court_owner_not_found(client, admin_token):
    resp = await client.post(
        "/admin/courts", json=_court_payload(99999), headers=_auth(admin_token)
    )
    assert resp.status_code == 422


async def test_create_court_missing_owner_id(client, admin_token):
    payload = _court_payload(1)
    payload.pop("owner_id")
    resp = await client.post("/admin/courts", json=payload, headers=_auth(admin_token))
    assert resp.status_code == 422


async def test_update_any_court(client, admin_token, db_session):
    owner = await _insert_user(db_session, "court_owner_d", role="venue_admin")
    court = await _insert_court(db_session, owner, "旧馆名")

    resp = await client.put(
        f"/admin/courts/{court.id}",
        json=_court_payload(owner, name="全局改名馆", type="网球", price="150", slot_minutes=120),
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "全局改名馆"
    assert data["type"] == "网球"
    row = await db_session.get(Court, court.id)
    await db_session.refresh(row)
    assert row.name == "全局改名馆"
    assert row.price == Decimal("150")


async def test_delete_court_without_bookings(client, admin_token, db_session):
    owner = await _insert_user(db_session, "court_owner_e", role="venue_admin")
    court = await _insert_court(db_session, owner, "待删馆")

    resp = await client.delete(f"/admin/courts/{court.id}", headers=_auth(admin_token))
    assert resp.status_code == 204
    # identity map 会缓存已加载对象，用 count 查询验证物理删除
    count = await db_session.scalar(
        select(func.count()).select_from(Court).where(Court.id == court.id)
    )
    assert count == 0


async def test_delete_court_with_bookings_conflict(client, admin_token, db_session):
    owner = await _insert_user(db_session, "court_owner_f", role="venue_admin")
    court = await _insert_court(db_session, owner, "有预定馆")
    ua = await _insert_user(db_session, "manage_user_a")
    await _insert_booking(db_session, ua, court.id, TOMORROW, time(9, 0))

    resp = await client.delete(f"/admin/courts/{court.id}", headers=_auth(admin_token))
    assert resp.status_code == 409
    assert resp.json()["detail"] == "该球场存在预定记录，不可删除"
    count = await db_session.scalar(
        select(func.count()).select_from(Court).where(Court.id == court.id)
    )
    assert count == 1


async def test_delete_court_not_found(client, admin_token):
    resp = await client.delete("/admin/courts/99999", headers=_auth(admin_token))
    assert resp.status_code == 404


async def test_list_all_bookings(client, admin_token, db_session):
    owner_a = await _insert_user(db_session, "court_owner_g", role="venue_admin")
    owner_b = await _insert_user(db_session, "court_owner_h", role="venue_admin")
    court_a = await _insert_court(db_session, owner_a, "丙馆")
    court_b = await _insert_court(db_session, owner_b, "丁馆", type_="篮球")
    ua = await _insert_user(db_session, "manage_user_b")
    ub = await _insert_user(db_session, "manage_user_c")
    b1 = await _insert_booking(db_session, ua, court_a.id, TOMORROW, time(9, 0))
    b2 = await _insert_booking(db_session, ub, court_b.id, TOMORROW, time(10, 0))

    resp = await client.get("/admin/bookings", headers=_auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert {b["id"] for b in data} == {b1, b2}
    by_id = {b["id"]: b for b in data}
    assert by_id[b1]["username"] == "manage_user_b"
    assert by_id[b1]["court_name"] == "丙馆"
    assert by_id[b2]["username"] == "manage_user_c"
    assert by_id[b2]["court_name"] == "丁馆"


async def test_cancel_any_booking_success(client, admin_token, db_session):
    owner = await _insert_user(db_session, "court_owner_i", role="venue_admin")
    court = await _insert_court(db_session, owner, "戊馆")
    ua = await _insert_user(db_session, "manage_user_d")
    booking_id = await _insert_booking(db_session, ua, court.id, TOMORROW, time(9, 0))

    resp = await client.delete(f"/admin/bookings/{booking_id}", headers=_auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "cancelled"
    assert data["username"] == "manage_user_d"
    assert data["court_name"] == "戊馆"
    row = await db_session.get(Booking, booking_id)
    assert row is not None  # 软取消：记录保留
    assert row.status == "cancelled"


async def test_cancel_any_booking_started_conflict(client, admin_token, db_session):
    owner = await _insert_user(db_session, "court_owner_j", role="venue_admin")
    court = await _insert_court(db_session, owner, "己馆")
    ua = await _insert_user(db_session, "manage_user_e")
    # 当天 00:00 的预定在任何运行时刻均已开始（直插绕过下单校验）
    booking_id = await _insert_booking(db_session, ua, court.id, date.today(), time(0, 0))

    resp = await client.delete(f"/admin/bookings/{booking_id}", headers=_auth(admin_token))
    assert resp.status_code == 409
    assert resp.json()["detail"] == "时段已开始，无法取消"


@pytest.mark.parametrize("status", ["checked_in", "cancelled"])
async def test_cancel_any_booking_invalid_status(client, admin_token, db_session, status):
    owner = await _insert_user(db_session, "court_owner_k", role="venue_admin")
    court = await _insert_court(db_session, owner, "庚馆")
    ua = await _insert_user(db_session, "manage_user_f")
    booking_id = await _insert_booking(db_session, ua, court.id, TOMORROW, time(9, 0), status=status)

    resp = await client.delete(f"/admin/bookings/{booking_id}", headers=_auth(admin_token))
    assert resp.status_code == 409


async def test_cancel_any_booking_not_found(client, admin_token):
    resp = await client.delete("/admin/bookings/99999", headers=_auth(admin_token))
    assert resp.status_code == 404


async def test_admin_manage_routes_forbidden_for_others(client, user_token, venue_admin_token):
    for token in (user_token, venue_admin_token):
        assert (await client.get("/admin/courts", headers=_auth(token))).status_code == 403
        assert (
            await client.post("/admin/courts", json=_court_payload(1), headers=_auth(token))
        ).status_code == 403
        assert (
            await client.put(
                "/admin/courts/1", json=_court_payload(1), headers=_auth(token)
            )
        ).status_code == 403
        assert (await client.delete("/admin/courts/1", headers=_auth(token))).status_code == 403
        assert (await client.get("/admin/bookings", headers=_auth(token))).status_code == 403
        assert (await client.delete("/admin/bookings/1", headers=_auth(token))).status_code == 403


async def test_admin_manage_routes_require_login(client):
    assert (await client.get("/admin/courts")).status_code == 401
    assert (await client.post("/admin/courts", json=_court_payload(1))).status_code == 401
    assert (await client.put("/admin/courts/1", json=_court_payload(1))).status_code == 401
    assert (await client.delete("/admin/courts/1")).status_code == 401
    assert (await client.get("/admin/bookings")).status_code == 401
    assert (await client.delete("/admin/bookings/1")).status_code == 401
