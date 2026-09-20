import pytest
from sqlalchemy import select

from app.models.application import Application
from app.models.user import User


async def _register_and_login(client, username: str) -> str:
    await client.post("/auth/register", json={"username": username, "password": "pass123"})
    resp = await client.post("/auth/login", json={"username": username, "password": "pass123"})
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_apply_success_sets_pending(client):
    token = await _register_and_login(client, "apply_ok01")
    resp = await client.post("/auth/apply-venue-admin", headers=_auth(token))
    assert resp.status_code == 201
    assert resp.json()["status"] == "pending"
    me = await client.get("/auth/me", headers=_auth(token))
    assert me.json()["application_status"] == "pending"


async def test_apply_duplicate_pending_conflict(client):
    token = await _register_and_login(client, "apply_dup01")
    first = await client.post("/auth/apply-venue-admin", headers=_auth(token))
    assert first.status_code == 201
    resp = await client.post("/auth/apply-venue-admin", headers=_auth(token))
    assert resp.status_code == 409
    assert resp.json()["detail"] == "已有待审批申请"


async def test_apply_approved_conflict(client, db_session):
    token = await _register_and_login(client, "apply_appr01")
    user = await db_session.scalar(select(User).where(User.username == "apply_appr01"))
    db_session.add(Application(user_id=user.id, status="approved"))
    await db_session.commit()
    resp = await client.post("/auth/apply-venue-admin", headers=_auth(token))
    assert resp.status_code == 409
    assert resp.json()["detail"] == "已是场地管理员"


async def test_apply_after_rejection_allowed(client, db_session):
    token = await _register_and_login(client, "apply_rej01")
    first = await client.post("/auth/apply-venue-admin", headers=_auth(token))
    assert first.status_code == 201
    user = await db_session.scalar(select(User).where(User.username == "apply_rej01"))
    application = await db_session.scalar(select(Application).where(Application.user_id == user.id))
    application.status = "rejected"
    await db_session.commit()
    resp = await client.post("/auth/apply-venue-admin", headers=_auth(token))
    assert resp.status_code == 201
    me = await client.get("/auth/me", headers=_auth(token))
    assert me.json()["application_status"] == "pending"


async def test_apply_requires_login(client):
    resp = await client.post("/auth/apply-venue-admin")
    assert resp.status_code == 401


@pytest.mark.parametrize("role", ["venue_admin", "admin"])
async def test_apply_forbidden_for_privileged_roles(client, db_session, role):
    username = f"apply_role_{role}_01"
    token = await _register_and_login(client, username)
    user = await db_session.scalar(select(User).where(User.username == username))
    user.role = role
    await db_session.commit()
    resp = await client.post("/auth/apply-venue-admin", headers=_auth(token))
    assert resp.status_code == 403
