from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config import settings


def _make_token(**overrides) -> str:
    payload = {"role": "user", "exp": datetime.now(timezone.utc) + timedelta(minutes=30)}
    payload.update(overrides)
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


async def test_register_success(client):
    resp = await client.post("/auth/register", json={"username": "alice01", "password": "pass123"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "alice01"
    assert data["role"] == "user"
    assert isinstance(data["id"], int)
    assert data["created_at"]
    assert "password_hash" not in data


async def test_register_duplicate_username(client):
    payload = {"username": "bob_dup01", "password": "pass123"}
    assert (await client.post("/auth/register", json=payload)).status_code == 201
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 409
    assert resp.json()["detail"] == "用户名已存在"


@pytest.mark.parametrize("username", ["ab", "bad$name", "has space", "x" * 33])
async def test_register_invalid_username(client, username):
    resp = await client.post("/auth/register", json={"username": username, "password": "pass123"})
    assert resp.status_code == 422


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("user_pwd_num", "12345678"),
        ("user_pwd_alpha", "abcdefgh"),
        ("user_pwd_short", "a1"),
    ],
)
async def test_register_invalid_password(client, username, password):
    resp = await client.post("/auth/register", json={"username": username, "password": password})
    assert resp.status_code == 422


async def test_login_success(client):
    await client.post("/auth/register", json={"username": "charlie01", "password": "pass123"})
    resp = await client.post("/auth/login", json={"username": "charlie01", "password": "pass123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "charlie01"
    assert data["user"]["role"] == "user"


async def test_login_wrong_password(client):
    await client.post("/auth/register", json={"username": "dave01", "password": "pass123"})
    resp = await client.post("/auth/login", json={"username": "dave01", "password": "wrong123"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "用户名或密码错误"
    # 不存在的用户与密码错误同文案，不区分
    resp2 = await client.post("/auth/login", json={"username": "nobody99", "password": "pass123"})
    assert resp2.status_code == 401
    assert resp2.json()["detail"] == "用户名或密码错误"


async def test_me_requires_token(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401

    await client.post("/auth/register", json={"username": "eve01", "password": "pass123"})
    login = await client.post("/auth/login", json={"username": "eve01", "password": "pass123"})
    token = login.json()["access_token"]
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "eve01"


async def test_me_forged_token(client):
    resp = await client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


async def test_me_application_status_null_when_no_application(client):
    await client.post("/auth/register", json={"username": "grace01", "password": "pass123"})
    login = await client.post("/auth/login", json={"username": "grace01", "password": "pass123"})
    token = login.json()["access_token"]
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["application_status"] is None


async def test_me_token_missing_sub(client):
    # 正确密钥签名但 payload 缺 sub：无效凭证必须 401 而非 500
    token = _make_token()
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


async def test_me_token_non_numeric_sub(client):
    # 正确密钥签名但 sub 非数字：无效凭证必须 401 而非 500
    token = _make_token(sub="abc")
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
