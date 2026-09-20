from datetime import time
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.court import Court
from app.models.user import User


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _user_id(db_session, username: str) -> int:
    user = await db_session.scalar(select(User).where(User.username == username))
    return user.id


async def _insert_user(db_session, username: str, role: str = "venue_admin") -> int:
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
    price: str = "80",
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


def _court_payload(**overrides) -> dict:
    payload = {
        "name": "新建测试馆",
        "type": "羽毛球",
        "price": "80",
        "open_time": "08:00:00",
        "close_time": "22:00:00",
        "slot_minutes": 60,
    }
    payload.update(overrides)
    return payload


async def test_my_courts_empty(client, venue_admin_token):
    resp = await client.get("/venue-admin/courts", headers=_auth(venue_admin_token))
    assert resp.status_code == 200
    assert resp.json() == []


async def test_my_courts_only_own(client, venue_admin_token, db_session):
    my_id = await _user_id(db_session, "fixture_venue_admin01")
    await _insert_court(db_session, my_id, "自己的羽毛球馆")
    other_id = await _insert_user(db_session, "court_other01")
    await _insert_court(db_session, other_id, "别人的网球馆", type_="网球")

    resp = await client.get("/venue-admin/courts", headers=_auth(venue_admin_token))
    assert resp.status_code == 200
    assert [c["name"] for c in resp.json()] == ["自己的羽毛球馆"]


async def test_update_foreign_court_hidden(client, venue_admin_token, court):
    # court fixture 属于 fixture_owner01，非当前 venue_admin：越权按不存在处理
    resp = await client.put(
        f"/venue-admin/courts/{court.id}",
        json=_court_payload(name="篡改"),
        headers=_auth(venue_admin_token),
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "球场不存在"


async def test_admin_can_manage_any_court(client, admin_token, court):
    resp = await client.put(
        f"/venue-admin/courts/{court.id}",
        json=_court_payload(name="管理员改名"),
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "管理员改名"


async def test_admin_list_sees_all(client, admin_token, db_session):
    other_id = await _insert_user(db_session, "court_other02")
    await _insert_court(db_session, other_id, "别人的馆")

    resp = await client.get("/venue-admin/courts", headers=_auth(admin_token))
    assert resp.status_code == 200
    assert [c["name"] for c in resp.json()] == ["别人的馆"]


async def test_create_court_success(client, venue_admin_token, db_session):
    resp = await client.post(
        "/venue-admin/courts", json=_court_payload(), headers=_auth(venue_admin_token)
    )
    assert resp.status_code == 201
    data = resp.json()
    row = await db_session.get(Court, data["id"])
    assert row is not None
    my_id = await _user_id(db_session, "fixture_venue_admin01")
    assert row.owner_id == my_id


@pytest.mark.parametrize(
    "overrides",
    [
        {"type": "乒乓球"},  # 类型非枚举
        {"slot_minutes": 90},  # 时段粒度非 60/120/180
        {"open_time": "10:00:00", "close_time": "09:00:00"},  # 开放时间晚于关闭时间
        {"price": "0"},  # 价格非正数
    ],
)
async def test_create_court_invalid_payload(client, venue_admin_token, overrides):
    resp = await client.post(
        "/venue-admin/courts", json=_court_payload(**overrides), headers=_auth(venue_admin_token)
    )
    assert resp.status_code == 422


async def test_update_court_fields(client, venue_admin_token, db_session):
    my_id = await _user_id(db_session, "fixture_venue_admin01")
    own = await _insert_court(db_session, my_id, "旧名字")

    resp = await client.put(
        f"/venue-admin/courts/{own.id}",
        json=_court_payload(name="新名字", type="篮球", price="120", slot_minutes=120),
        headers=_auth(venue_admin_token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "新名字"
    assert data["type"] == "篮球"
    assert data["slot_minutes"] == 120
    row = await db_session.get(Court, own.id)
    await db_session.refresh(row)  # 外部 session 已更新该行，强制从库重读
    assert row.name == "新名字"
    assert row.price == Decimal("120")


async def test_venue_admin_routes_forbidden_for_user(client, user_token):
    assert (await client.get("/venue-admin/courts", headers=_auth(user_token))).status_code == 403
    assert (
        await client.post("/venue-admin/courts", json=_court_payload(), headers=_auth(user_token))
    ).status_code == 403


async def test_venue_admin_routes_require_login(client):
    assert (await client.get("/venue-admin/courts")).status_code == 401
    assert (await client.post("/venue-admin/courts", json=_court_payload())).status_code == 401
