from datetime import time
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app import models  # noqa: F401  确保模型注册到 Base.metadata
from app.db import Base, get_db
from app.main import app

TEST_DATABASE_URL = "postgresql+asyncpg://gym_app:CHANGE_ME@localhost:5432/gym_booking_test"


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(autouse=True)
async def _clean_tables(test_engine):
    # 测试库为会话级共享：每个用例前清空数据，避免跨用例残留互相污染
    async with test_engine.begin() as conn:
        await conn.execute(delete(models.Booking))
        await conn.execute(delete(models.Application))
        await conn.execute(delete(models.Court))
        await conn.execute(delete(models.User))
    yield


@pytest.fixture
async def client(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def db_session(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def user_token(client) -> str:
    await client.post("/auth/register", json={"username": "fixture_user01", "password": "pass123"})
    resp = await client.post("/auth/login", json={"username": "fixture_user01", "password": "pass123"})
    return resp.json()["access_token"]


async def _register_and_set_role(client, db_session, username: str, role: str) -> str:
    await client.post("/auth/register", json={"username": username, "password": "pass123"})
    login = await client.post("/auth/login", json={"username": username, "password": "pass123"})
    user = await db_session.scalar(select(models.User).where(models.User.username == username))
    user.role = role
    await db_session.commit()
    return login.json()["access_token"]


@pytest.fixture
async def venue_admin_token(client, db_session) -> str:
    return await _register_and_set_role(client, db_session, "fixture_venue_admin01", "venue_admin")


@pytest.fixture
async def admin_token(client, db_session) -> str:
    return await _register_and_set_role(client, db_session, "fixture_admin01", "admin")


@pytest.fixture
async def court(db_session) -> models.Court:
    owner = models.User(username="fixture_owner01", password_hash="not-used", role="venue_admin")
    db_session.add(owner)
    await db_session.flush()
    court = models.Court(
        owner_id=owner.id,
        name="测试羽毛球馆",
        type="羽毛球",
        price=Decimal("80"),
        open_time=time(8, 0),
        close_time=time(22, 0),
        slot_minutes=60,
    )
    db_session.add(court)
    await db_session.commit()
    await db_session.refresh(court)
    return court
