import pytest
from sqlalchemy import select

from app.models.application import Application
from app.models.user import User


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


async def _insert_application(db_session, user_id: int, status: str = "pending") -> int:
    application = Application(user_id=user_id, status=status)
    db_session.add(application)
    await db_session.commit()
    await db_session.refresh(application)
    return application.id


async def test_list_users_all_and_role_filter(client, admin_token, db_session):
    await _insert_user(db_session, "plain_user01", role="user")
    await _insert_user(db_session, "va_user01", role="venue_admin")
    # fixture_admin01（admin_token fixture 创建）本身也在库中

    resp = await client.get("/admin/users", headers=_auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert {u["username"] for u in data} == {"fixture_admin01", "plain_user01", "va_user01"}
    assert all("password_hash" not in u for u in data)

    resp = await client.get("/admin/users?role=user", headers=_auth(admin_token))
    assert resp.status_code == 200
    assert [u["username"] for u in resp.json()] == ["plain_user01"]


async def test_update_role_success_and_takes_effect(client, admin_token, user_token, db_session):
    target_id = await _user_id(db_session, "fixture_user01")

    resp = await client.put(
        f"/admin/users/{target_id}/role",
        json={"role": "venue_admin"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "venue_admin"
    # 角色即时生效：被改用户持旧 token 访问 venue-admin 接口成功（get_current_user 每次读库）
    resp = await client.get("/venue-admin/courts", headers=_auth(user_token))
    assert resp.status_code == 200


async def test_update_role_invalid_value(client, admin_token, db_session):
    other_id = await _insert_user(db_session, "role_target01")

    resp = await client.put(
        f"/admin/users/{other_id}/role",
        json={"role": "superuser"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 422


async def test_update_own_role_conflict(client, admin_token, db_session):
    # SPEC-D2：不能修改自己的角色，防止管理员锁死自己
    my_id = await _user_id(db_session, "fixture_admin01")
    resp = await client.put(
        f"/admin/users/{my_id}/role", json={"role": "user"}, headers=_auth(admin_token)
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "不能修改自己的角色"


async def test_update_role_user_not_found(client, admin_token):
    resp = await client.put(
        "/admin/users/99999/role", json={"role": "user"}, headers=_auth(admin_token)
    )
    assert resp.status_code == 404


async def test_list_applications_with_filter_and_username(client, admin_token, db_session):
    ua = await _insert_user(db_session, "apply_user_a")
    ub = await _insert_user(db_session, "apply_user_b")
    app1 = await _insert_application(db_session, ua, status="pending")
    await _insert_application(db_session, ub, status="approved")
    # 驳回后可重新申请（Q-14）：同一用户第二条 pending
    app2 = await _insert_application(db_session, ua, status="pending")

    resp = await client.get("/admin/applications", headers=_auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    usernames = {a["id"]: a["username"] for a in data}
    assert usernames[app1] == "apply_user_a"
    assert usernames[app2] == "apply_user_a"
    assert all(a["user_id"] for a in data)

    resp = await client.get("/admin/applications?status=pending", headers=_auth(admin_token))
    assert resp.status_code == 200
    assert [a["id"] for a in resp.json()] == [app1, app2]


async def test_approve_application_success(client, admin_token, user_token, db_session):
    # 端到端：注册用户提交申请 → admin 批准 → 角色升级、venue-admin 接口可用
    resp = await client.post("/auth/apply-venue-admin", headers=_auth(user_token))
    assert resp.status_code == 201
    application_id = resp.json()["id"]
    user_id = await _user_id(db_session, "fixture_user01")

    resp = await client.post(
        f"/admin/applications/{application_id}/approve", headers=_auth(admin_token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    assert data["username"] == "fixture_user01"
    assert data["reviewed_at"] is not None

    row = await db_session.get(Application, application_id)
    await db_session.refresh(row)
    assert row.status == "approved"
    assert row.reviewed_at is not None
    user = await db_session.get(User, user_id)
    await db_session.refresh(user)
    assert user.role == "venue_admin"
    # 升级后旧 token 即可访问 venue-admin 接口
    resp = await client.get("/venue-admin/courts", headers=_auth(user_token))
    assert resp.status_code == 200


async def test_reject_application_keeps_role(client, admin_token, db_session):
    ua = await _insert_user(db_session, "apply_user_c", role="user")
    application_id = await _insert_application(db_session, ua, status="pending")

    resp = await client.post(
        f"/admin/applications/{application_id}/reject", headers=_auth(admin_token)
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"

    row = await db_session.get(Application, application_id)
    await db_session.refresh(row)
    assert row.status == "rejected"
    user = await db_session.get(User, ua)
    await db_session.refresh(user)
    assert user.role == "user"  # 驳回不改角色


@pytest.mark.parametrize(
    "initial,action",
    [
        ("approved", "approve"),
        ("approved", "reject"),
        ("rejected", "approve"),
        ("rejected", "reject"),
    ],
)
async def test_review_non_pending_conflict(client, admin_token, db_session, initial, action):
    ua = await _insert_user(db_session, f"apply_user_{initial}_{action}")
    application_id = await _insert_application(db_session, ua, status=initial)

    resp = await client.post(
        f"/admin/applications/{application_id}/{action}", headers=_auth(admin_token)
    )
    assert resp.status_code == 409
    assert resp.json()["detail"] == "该申请已处理"


async def test_review_application_not_found(client, admin_token):
    resp = await client.post("/admin/applications/99999/approve", headers=_auth(admin_token))
    assert resp.status_code == 404
    assert resp.json()["detail"] == "申请不存在"


async def test_admin_routes_forbidden_for_others(client, user_token, venue_admin_token):
    for token in (user_token, venue_admin_token):
        assert (await client.get("/admin/users", headers=_auth(token))).status_code == 403
        assert (
            await client.put(
                "/admin/users/1/role", json={"role": "user"}, headers=_auth(token)
            )
        ).status_code == 403
        assert (await client.get("/admin/applications", headers=_auth(token))).status_code == 403
        assert (
            await client.post("/admin/applications/1/approve", headers=_auth(token))
        ).status_code == 403


async def test_admin_routes_require_login(client):
    assert (await client.get("/admin/users")).status_code == 401
    assert (await client.put("/admin/users/1/role", json={"role": "user"})).status_code == 401
    assert (await client.get("/admin/applications")).status_code == 401
    assert (await client.post("/admin/applications/1/approve")).status_code == 401
