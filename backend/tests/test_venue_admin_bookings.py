from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.booking import Booking
from app.models.court import Court
from app.models.user import User

TOMORROW = date.today() + timedelta(days=1)
DAY_AFTER = date.today() + timedelta(days=2)
CURRENT_MONTH = date.today().strftime("%Y-%m")


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


async def test_list_venue_bookings_only_own_with_username_and_filters(
    client, venue_admin_token, db_session
):
    my_id = await _user_id(db_session, "fixture_venue_admin01")
    court1 = await _insert_court(db_session, my_id, "我的羽毛球馆")
    court2 = await _insert_court(db_session, my_id, "我的篮球馆", type_="篮球")
    other_admin_id = await _insert_user(db_session, "other_owner01", role="venue_admin")
    other_court = await _insert_court(db_session, other_admin_id, "别人的馆")
    ua = await _insert_user(db_session, "booking_user_a")
    ub = await _insert_user(db_session, "booking_user_b")

    b1 = await _insert_booking(db_session, ua, court1.id, TOMORROW, time(9, 0))
    b2 = await _insert_booking(db_session, ub, court1.id, DAY_AFTER, time(10, 0))
    b3 = await _insert_booking(db_session, ub, court2.id, TOMORROW, time(11, 0))
    # 他人球场下的预定：不应出现
    await _insert_booking(db_session, ua, other_court.id, TOMORROW, time(12, 0))

    resp = await client.get("/venue-admin/bookings", headers=_auth(venue_admin_token))
    assert resp.status_code == 200
    data = resp.json()
    # 排序：date DESC / start_time DESC（与 /bookings/my 一致）
    assert [b["id"] for b in data] == [b2, b3, b1]
    usernames = {b["id"]: b["username"] for b in data}
    assert usernames[b1] == "booking_user_a"
    assert usernames[b2] == "booking_user_b"
    assert all(b["court_name"] for b in data)

    # ?court_id= 筛选
    resp = await client.get(
        f"/venue-admin/bookings?court_id={court1.id}", headers=_auth(venue_admin_token)
    )
    assert [b["id"] for b in resp.json()] == [b2, b1]

    # ?date= 筛选（日视图数据源，Q-17 基线）
    resp = await client.get(
        f"/venue-admin/bookings?date={TOMORROW}", headers=_auth(venue_admin_token)
    )
    assert [b["id"] for b in resp.json()] == [b3, b1]

    # 组合筛选
    resp = await client.get(
        f"/venue-admin/bookings?court_id={court1.id}&date={TOMORROW}",
        headers=_auth(venue_admin_token),
    )
    assert [b["id"] for b in resp.json()] == [b1]


async def test_list_foreign_court_bookings_empty(client, venue_admin_token, db_session):
    other_admin_id = await _insert_user(db_session, "other_owner02", role="venue_admin")
    other_court = await _insert_court(db_session, other_admin_id, "别人的馆")
    ua = await _insert_user(db_session, "booking_user_c")
    await _insert_booking(db_session, ua, other_court.id, TOMORROW, time(9, 0))

    resp = await client.get("/venue-admin/bookings", headers=_auth(venue_admin_token))
    assert resp.status_code == 200
    assert resp.json() == []
    # 显式按他人球场筛选同样拿不到（owner 过滤而非报错）
    resp = await client.get(
        f"/venue-admin/bookings?court_id={other_court.id}", headers=_auth(venue_admin_token)
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_calendar_month_view(client, venue_admin_token, db_session):
    my_id = await _user_id(db_session, "fixture_venue_admin01")
    court1 = await _insert_court(db_session, my_id, "我的羽毛球馆")
    ua = await _insert_user(db_session, "booking_user_d")
    in_month_day = date(date.today().year, date.today().month, 15)
    prev_last = date(date.today().year, date.today().month, 1) - timedelta(days=1)
    out_month_day = date(prev_last.year, prev_last.month, 10)

    b_early = await _insert_booking(db_session, ua, court1.id, in_month_day, time(11, 0))
    b_late = await _insert_booking(db_session, ua, court1.id, in_month_day + timedelta(days=1), time(9, 0))
    # 上月的预定：不应出现在当月日历
    await _insert_booking(db_session, ua, court1.id, out_month_day, time(9, 0))

    resp = await client.get(
        f"/venue-admin/bookings/calendar?month={CURRENT_MONTH}", headers=_auth(venue_admin_token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert [b["id"] for b in data] == [b_early, b_late]
    assert data[0]["username"] == "booking_user_d"
    assert data[0]["court_name"] == "我的羽毛球馆"

    # 日视图复用 ?date= 筛选
    resp = await client.get(
        f"/venue-admin/bookings?date={in_month_day}", headers=_auth(venue_admin_token)
    )
    assert [b["id"] for b in resp.json()] == [b_early]


@pytest.mark.parametrize("month", ["2026-13", "not-a-month"])
async def test_calendar_invalid_month_format(client, venue_admin_token, month):
    resp = await client.get(
        f"/venue-admin/bookings/calendar?month={month}", headers=_auth(venue_admin_token)
    )
    assert resp.status_code == 422


async def test_check_in_booking_success(client, venue_admin_token, db_session):
    my_id = await _user_id(db_session, "fixture_venue_admin01")
    court1 = await _insert_court(db_session, my_id, "我的羽毛球馆")
    ua = await _insert_user(db_session, "booking_user_e")
    booking_id = await _insert_booking(db_session, ua, court1.id, TOMORROW, time(9, 0))

    resp = await client.post(
        f"/venue-admin/bookings/{booking_id}/check-in", headers=_auth(venue_admin_token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "checked_in"
    assert data["username"] == "booking_user_e"
    assert data["court_name"] == "我的羽毛球馆"
    row = await db_session.get(Booking, booking_id)
    await db_session.refresh(row)  # 外部 session 已更新该行，强制从库重读
    assert row.status == "checked_in"


async def test_check_in_repeat_conflict(client, venue_admin_token, db_session):
    my_id = await _user_id(db_session, "fixture_venue_admin01")
    court1 = await _insert_court(db_session, my_id, "我的羽毛球馆")
    ua = await _insert_user(db_session, "booking_user_f")
    booking_id = await _insert_booking(
        db_session, ua, court1.id, TOMORROW, time(9, 0), status="checked_in"
    )

    resp = await client.post(
        f"/venue-admin/bookings/{booking_id}/check-in", headers=_auth(venue_admin_token)
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "已核销"


async def test_check_in_cancelled_conflict(client, venue_admin_token, db_session):
    my_id = await _user_id(db_session, "fixture_venue_admin01")
    court1 = await _insert_court(db_session, my_id, "我的羽毛球馆")
    ua = await _insert_user(db_session, "booking_user_g")
    booking_id = await _insert_booking(
        db_session, ua, court1.id, TOMORROW, time(9, 0), status="cancelled"
    )

    resp = await client.post(
        f"/venue-admin/bookings/{booking_id}/check-in", headers=_auth(venue_admin_token)
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "当前状态不可核销"


async def test_check_in_foreign_court_booking_not_found(client, venue_admin_token, court, db_session):
    # court fixture 属于 fixture_owner01，非当前 venue_admin：越权按不存在处理
    ua = await _insert_user(db_session, "booking_user_h")
    booking_id = await _insert_booking(db_session, ua, court.id, TOMORROW, time(9, 0))

    resp = await client.post(
        f"/venue-admin/bookings/{booking_id}/check-in", headers=_auth(venue_admin_token)
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "预定不存在"


async def test_check_in_booking_not_found(client, venue_admin_token):
    resp = await client.post("/venue-admin/bookings/99999/check-in", headers=_auth(venue_admin_token))
    assert resp.status_code == 404


async def test_cancel_venue_booking_success(client, venue_admin_token, db_session):
    my_id = await _user_id(db_session, "fixture_venue_admin01")
    court1 = await _insert_court(db_session, my_id, "我的羽毛球馆")
    ua = await _insert_user(db_session, "booking_user_i")
    booking_id = await _insert_booking(db_session, ua, court1.id, TOMORROW, time(9, 0))

    resp = await client.delete(
        f"/venue-admin/bookings/{booking_id}", headers=_auth(venue_admin_token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "cancelled"
    assert data["username"] == "booking_user_i"
    row = await db_session.get(Booking, booking_id)
    assert row is not None  # 软取消：记录保留
    assert row.status == "cancelled"


async def test_cancel_venue_booking_started_conflict(client, venue_admin_token, db_session):
    my_id = await _user_id(db_session, "fixture_venue_admin01")
    court1 = await _insert_court(db_session, my_id, "我的羽毛球馆")
    ua = await _insert_user(db_session, "booking_user_j")
    # 当天 00:00 的预定在任何运行时刻均已开始（直插绕过下单校验）
    booking_id = await _insert_booking(db_session, ua, court1.id, date.today(), time(0, 0))

    resp = await client.delete(
        f"/venue-admin/bookings/{booking_id}", headers=_auth(venue_admin_token)
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "时段已开始，无法取消"


@pytest.mark.parametrize("status", ["checked_in", "cancelled"])
async def test_cancel_venue_booking_invalid_status(client, venue_admin_token, db_session, status):
    my_id = await _user_id(db_session, "fixture_venue_admin01")
    court1 = await _insert_court(db_session, my_id, "我的羽毛球馆")
    ua = await _insert_user(db_session, "booking_user_k")
    booking_id = await _insert_booking(db_session, ua, court1.id, TOMORROW, time(9, 0), status=status)

    resp = await client.delete(
        f"/venue-admin/bookings/{booking_id}", headers=_auth(venue_admin_token)
    )
    assert resp.status_code == 409


async def test_cancel_foreign_court_booking_not_found(client, venue_admin_token, court, db_session):
    ua = await _insert_user(db_session, "booking_user_l")
    booking_id = await _insert_booking(db_session, ua, court.id, TOMORROW, time(9, 0))

    resp = await client.delete(
        f"/venue-admin/bookings/{booking_id}", headers=_auth(venue_admin_token)
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "预定不存在"


async def test_cancel_venue_booking_not_found(client, venue_admin_token):
    resp = await client.delete("/venue-admin/bookings/99999", headers=_auth(venue_admin_token))
    assert resp.status_code == 404


async def test_venue_booking_routes_forbidden_for_user(client, user_token):
    assert (await client.get("/venue-admin/bookings", headers=_auth(user_token))).status_code == 403
    assert (
        await client.get(
            f"/venue-admin/bookings/calendar?month={CURRENT_MONTH}", headers=_auth(user_token)
        )
    ).status_code == 403
    assert (
        await client.post("/venue-admin/bookings/1/check-in", headers=_auth(user_token))
    ).status_code == 403
    assert (await client.delete("/venue-admin/bookings/1", headers=_auth(user_token))).status_code == 403


async def test_venue_booking_routes_require_login(client):
    assert (await client.get("/venue-admin/bookings")).status_code == 401
    assert (
        await client.get(f"/venue-admin/bookings/calendar?month={CURRENT_MONTH}")
    ).status_code == 401
    assert (await client.post("/venue-admin/bookings/1/check-in")).status_code == 401
    assert (await client.delete("/venue-admin/bookings/1")).status_code == 401
