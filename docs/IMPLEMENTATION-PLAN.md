# 球场预定管理系统 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 subagent-driven-development（推荐）或 executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 实现球场预定管理系统的完整业务闭环（注册 → 浏览/筛选 → 预定 → 核销 → 全局管理），覆盖三种角色 + 游客。

**架构：** 前后端分离。前端 Next.js 15（App Router + TypeScript + Tailwind 4）通过 REST API + JWT Bearer 与后端通信；后端 FastAPI 单体（routers / schemas / models / security 分层 + Alembic 迁移）连接本机 PostgreSQL 17；防超订由 `bookings` 表唯一约束 + 事务硬保证，禁止仅依赖应用层判断。

**技术栈：** Next.js 15.5.x / TypeScript 5.x / Tailwind CSS 4.x / React 19 / Python 3.12+ / FastAPI ≥0.115 / SQLAlchemy 2.x（asyncpg）/ Alembic 1.x / PostgreSQL 17 / PyJWT + passlib（bcrypt）。

**规格：** [SPEC.md](SPEC.md)（技术规格说明书 v0.1）+ [PRD.md](PRD.md)（产品需求 v1.0）。本计划已替代 `.claude/github-atomic-flame.md`（旧计划保留不动，仅作历史参考）。

## 基线决策表（执行前请确认）

PRD 的 27 项待确认事项（Q-01 ~ Q-27）在本计划中按下表「基线取值」执行（即 PRD 建议默认值）。**执行开工前请逐行确认本表**；产品侧后续敲定的取值与基线不符时，仅需修订对应任务，不影响计划结构。

| 编号 | 事项 | 基线取值 | 备注 |
|---|---|---|---|
| Q-01 | 产品名称 | 「球场预定管理系统」 | |
| Q-02 | 注册字段 | 用户名 + 密码 | 用户名规则为本计划补充：3-32 位字母/数字/下划线，唯一 |
| Q-03 | 密码规则 | ≥6 位，必须同时包含字母和数字；不做找回 | |
| Q-04 | 下单角色 | 仅普通用户（user）可下单 | venue_admin / admin 调用 POST /bookings 返回 403 |
| Q-05 | 预定状态 | `booked` / `checked_in` / `cancelled` | 过期未核销由前端展示「已过期」，不新增状态 |
| Q-06 | 取消时限 | 仅时段开始前可取消 | ⚠ 基线统一适用于用户、场地管理员、系统管理员三种取消场景，执行前确认 |
| Q-07 | 价格口径 | 场地一口价 `Court.price`，无分时定价 | |
| Q-08 | 场地类型 | 羽毛球 / 篮球 / 网球 / 足球 | 枚举常量定义于 `schemas/courts.py`，可扩展 |
| Q-09 | 时段粒度 | 60 / 120 / 180 分钟三档，默认 60 | ⚠ SPEC-1：与 PRD 5.2 正文（默认 60 可配 30）冲突，执行前需裁定；本计划按三档实现 |
| Q-10 | 跨日营业 | 不支持，`open_time` < `close_time` | |
| Q-11 | 支付 mock | `Booking.price` 下单时快照 + `paid`（默认 false），UI 无支付步骤 | |
| Q-12 | seed 凭据 | 写入 backend `.env`，README 记录说明 | `.env` 不入库 |
| Q-13 | 用户管理范围 | 查看 + 角色管理；不做禁用/删除 | |
| Q-14 | 申请规则 | 驳回后可重新申请；已有 approved 记录则入口隐藏、后端 409 拒绝重复申请 | 申请状态查询见 SPEC-D1 |
| Q-15 | JWT 有效期 | 固定 24h，无刷新机制 | |
| Q-16 | 时区 | `date` 存日期；「当天」按服务端本机时区计算 | |
| Q-17 | 日历粒度 | 月视图 + 日视图切换 | |
| Q-18 | 球场图片 | 不做上传，保留 `image_url` 字段（可空） | |
| Q-19 | booked-slots 接口 | `GET /courts/{id}/booked-slots?date=YYYY-MM-DD` → 该日期已订时段的 `start_time` 字符串列表 | SPEC-2 响应结构按此基线 |
| Q-20 | 预约范围 | 今天起 7 天（今天 ≤ date ≤ 今天+6） | |
| Q-21 | 并发测试工具 | pytest + httpx + asyncio（任务 8） | |
| Q-22 | 里程碑日期 | 不设时间点，按任务顺序执行 | |
| Q-23 | PostgreSQL 版本 | 以 17 为准（18 兼容） | |
| Q-24 | 性能 | 常规接口 < 1s（本机环境），验收时目测确认 | |
| Q-25 | 浏览器 | 现代浏览器最新两个大版本（Chrome/Edge 最新版验收） | |
| Q-26 | 核销方式 | 场地管理员手动点击核销，无二维码 | |
| Q-27 | 用户故事/流程 | 按 PRD 第 6、7 章推导内容执行 | |
| SPEC-3 | 场地详情 | 独立页面 `/venues/[courtId]`，展示名称/类型/价格/开放时间/时段划分 + 「去预定」按钮 | ⚠ PRD F-USER-3 原文待确认，执行前确认 |
| SPEC-D1 | 申请状态查询 | `GET /auth/me` 响应含 `application_status`（最近一次申请状态，无申请为 null） | SPEC 7.2 未列，为支撑 Q-14 前端交互补充 |
| SPEC-D2 | admin 防锁死 | `PUT /admin/users/{id}/role` 目标为本人时返回 409「不能修改自己的角色」 | 本计划补充规则 |

## 全局约束

每条约束适用于本计划所有任务，数值从 SPEC 逐字照抄：

- Node.js ≥ 20 LTS；Next.js 15.5.x（App Router，已验证版本 `^15.5.9`）
- 前端语言 TypeScript 5.x 必用，所有组件/页面/API 调用使用 `.ts` / `.tsx`，**禁止 `.js`**
- Tailwind CSS 4.x（`@tailwindcss/postcss`）
- Python 3.12+；FastAPI ≥ 0.115（PyPI 最新稳定版）
- SQLAlchemy 2.x 异步 + `asyncpg`；Alembic 1.x 迁移；所有 schema 变更必须走 Alembic，禁止手工改表
- PostgreSQL 17（本机安装；18 兼容），数据库名 `gym_booking`
- 认证：JWT（`PyJWT`）Bearer，payload 含 `sub`（user_id）、`role`、`exp`；有效期固定 24h 无刷新
- 密码 bcrypt 哈希（passlib），≥6 位且同时包含字母和数字，禁止明文
- 角色：`user` / `venue_admin` / `admin`；系统管理员仅由 seed 脚本创建，不开放注册
- 错误语义：401 未登录 / 403 无权限 / 404 资源不存在 / 409 业务冲突（含防超订）/ 422 参数校验失败；错误体为 FastAPI 默认 `{"detail": "..."}`
- 防超订：`bookings` 表 `UNIQUE (court_id, date, start_time)`；创建预定在事务内 INSERT，IntegrityError → 409「该时段已被预约」
- 数据权限：场地管理员所有查询与操作按 `Court.owner_id == current_user.id` 过滤；系统管理员不受限；在 venue_admin 路由层用统一 dependency 实现
- CORS 仅放行 `http://localhost:3000`
- 密钥与凭据（JWT_SECRET、数据库口令、seed 管理员密码）写入 `.env`，`.gitignore` 排除，禁止提交代码库
- 前端仅通过 REST API 访问后端，禁止直连数据库；API 契约以 `http://localhost:8000/docs` 为准
- 时段网格数据来源：`GET /courts/{id}/booked-slots?date=YYYY-MM-DD`
- 可预约日期范围：今天起 7 天；取消仅限时段开始前；仅普通用户可下单
- 场地类型枚举：羽毛球/篮球/网球/足球；不支持跨日营业（`open_time` < `close_time`）
- 预定状态：`booked` / `checked_in` / `cancelled`；过期未核销前端展示「已过期」，不新增状态
- 价格：按场地一口价 `Court.price`；`Booking` 存 `price` 快照 + `paid`（mock，无支付流程）
- 日历视图：月视图 + 日视图切换；核销为管理员手动点击，不引入二维码
- 用户管理范围：查看 + 角色管理，不做禁用/删除
- 申请规则：被驳回后可重新申请；已通过后入口隐藏
- `date` 存日期，服务端按本机时区计算「当天」；常规接口响应 < 1s（本机环境）
- 每个任务结束必须 commit（消息用简洁英文，见各任务 Commit 步骤）；提交前先 `git status --short` / `git diff --stat` 展示变更摘要
- Windows 11 本机环境，命令按 Git Bash 执行；后端命令在 `backend/` 目录下执行，前端命令在 `frontend/` 目录下执行

## 文件结构

| 文件 | 职责 |
|---|---|
| `.gitignore` | 排除 node_modules / .next / .venv / __pycache__ / .env / .pytest_cache 等 |
| `README.md` | 项目简介、启动方式、seed 管理员凭据说明 |
| `docs/IMPLEMENTATION-PLAN.md` | 本计划（执行时勾选步骤复选框） |
| `backend/requirements.txt` | Python 依赖清单 |
| `backend/.env` | 本机配置（不入库）：DATABASE_URL / JWT_SECRET / SEED_ADMIN_* |
| `backend/.env.example` | 配置模板（入库），记录字段说明 |
| `backend/app/main.py` | FastAPI 入口 + CORS + 路由注册 |
| `backend/app/config.py` | pydantic-settings 读取 `.env` |
| `backend/app/db.py` | async engine / sessionmaker / `get_db` 依赖 / `Base` |
| `backend/app/models/` | user.py / application.py / court.py / booking.py + `__init__.py` |
| `backend/app/schemas/` | 请求/响应 Pydantic v2 模型，按路由模块拆分 |
| `backend/app/routers/` | auth.py / courts.py / bookings.py / venue_admin.py / admin.py |
| `backend/app/security.py` | bcrypt 哈希、JWT 签发/校验、`get_current_user` / `require_role` 依赖 |
| `backend/app/seed.py` | 初始化系统管理员（幂等） |
| `backend/alembic/` + `alembic.ini` | 数据库迁移 |
| `backend/tests/` | conftest.py + 按模块拆分的 pytest 用例 |
| `frontend/src/app/` | 页面：login / register / venues（+`[courtId]`）/ book/[courtId] / orders / me / venue-admin / admin |
| `frontend/src/lib/api.ts` | fetch 封装：baseURL、token 注入、401 跳转、错误解析 |
| `frontend/src/lib/types.ts` | 与后端 schema 对应的 TS 类型 |
| `frontend/src/lib/auth.ts` | token 存取（localStorage）、登录态判断 |
| `frontend/.env.local` | `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` |

---

## M1 初始化

### 任务 1：项目初始化（git + .gitignore + README）

**文件：**
- 创建：`.gitignore`、`README.md`

- [x] **步骤 1：初始化 git 仓库**

```bash
cd /e/Dev/aicoding/demo260920-gym
git init
```

- [x] **步骤 2：创建 `.gitignore`**

```gitignore
# Node
node_modules/
.next/
out/
npm-debug.log*

# Python
.venv/
__pycache__/
*.pyc
.pytest_cache/

# 环境配置（含密钥，禁止入库）
.env
.env.local

# IDE
.idea/
.vscode/
```

- [x] **步骤 3：创建 `README.md`**，含以下内容：

```markdown
# 球场预定管理系统

学习 / Demo / 毕设项目。Next.js 15 + FastAPI + PostgreSQL 17，实现球场浏览、分时段预定、核销与全局管理的完整业务闭环。

## 目录结构

- `frontend/` — Next.js 15（App Router + TypeScript + Tailwind 4），页面与交互
- `backend/` — FastAPI + SQLAlchemy（异步）+ Alembic，REST API 与数据模型
- `docs/` — PRD.md（产品需求）/ SPEC.md（技术规格）/ IMPLEMENTATION-PLAN.md（实施计划）

## 启动方式

1. 数据库：本机 PostgreSQL 17，数据库 `gym_booking`（配置见 `backend/.env.example`）
2. 后端：`cd backend && python -m venv .venv && source .venv/Scripts/activate && pip install -r requirements.txt && alembic upgrade head && python -m app.seed && uvicorn app.main:app --reload`，Swagger 文档 http://localhost:8000/docs
3. 前端：`cd frontend && npm install && npm run dev`，访问 http://localhost:3000
```

- [x] **步骤 4：验证**

```bash
git status --short
```

预期：`.gitignore`、`README.md` 出现在未跟踪列表。

- [x] **步骤 5：Commit**

```bash
git status --short && git diff --stat
git add .gitignore README.md
git commit -m "chore: init repo with gitignore and readme"
```

### 任务 2：本机 PostgreSQL 准备

**文件：**
- 创建：`backend/.env.example`、`backend/.env`（本机，不入库）

- [x] **步骤 1：检查 PostgreSQL 是否已安装**

```bash
psql --version
```

预期：输出 `psql (PostgreSQL) 17.x`。若未安装或版本不是 17，执行步骤 2；否则跳到步骤 3。

- [x] **步骤 2：安装 PostgreSQL 17**（仅当步骤 1 不满足时执行）

```bash
winget install --id PostgreSQL.PostgreSQL.17 -e
```

安装时记录 postgres 超级用户密码；安装完成后重开终端使 `psql` 进入 PATH。

- [x] **步骤 3：创建配置模板 `backend/.env.example`**

```ini
# 数据库连接（asyncpg 驱动）
DATABASE_URL=postgresql+asyncpg://gym_app:CHANGE_ME@localhost:5432/gym_booking
# JWT 签名密钥（生产请用 64 位随机串，例如 python -c "import secrets; print(secrets.token_hex(32))"）
JWT_SECRET=CHANGE_ME
# JWT 有效期（分钟），固定 24h 无刷新
JWT_EXPIRES_MINUTES=1440
# seed 初始系统管理员凭据（仅本地学习用途）
SEED_ADMIN_USERNAME=admin
SEED_ADMIN_PASSWORD=CHANGE_ME
```

- [x] **步骤 4：创建本机 `backend/.env`**（复制模板并填写真实值；此文件已被 `.gitignore` 排除）

```bash
mkdir -p backend && cp backend/.env.example backend/.env
```

用 `python -c "import secrets; print(secrets.token_hex(32))"` 生成 JWT_SECRET，替换 `CHANGE_ME`。

- [x] **步骤 5：创建数据库与账号**

```bash
psql -U postgres -c "CREATE USER gym_app WITH PASSWORD '你设置的口令';"
psql -U postgres -c "CREATE DATABASE gym_booking OWNER gym_app;"
```

- [x] **步骤 6：验证连接**

```bash
psql "postgresql://gym_app:你设置的口令@localhost:5432/gym_booking" -c "SELECT version();"
```

预期：输出 `PostgreSQL 17.x`。

- [x] **步骤 7：Commit**

```bash
git status --short && git diff --stat
git add backend/.env.example
git commit -m "chore: add backend env template"
```

## M3 后端

### 任务 3：FastAPI 骨架（config / db / main + 测试基建）

**前置：** 任务 2

**文件：**
- 创建：`backend/requirements.txt`、`backend/app/__init__.py`、`backend/app/main.py`、`backend/app/config.py`、`backend/app/db.py`、`backend/tests/__init__.py`、`backend/tests/conftest.py`

- [x] **步骤 1：创建 `backend/requirements.txt`**

```
fastapi>=0.115
uvicorn[standard]
sqlalchemy[asyncio]>=2.0
asyncpg
alembic>=1.13
pydantic-settings
PyJWT
passlib[bcrypt]
pytest
pytest-asyncio
httpx
```

- [x] **步骤 2：创建虚拟环境并安装依赖**

```bash
cd backend && python -m venv .venv && source .venv/Scripts/activate && pip install -r requirements.txt
```

验证：`python --version` 输出 3.12+。

- [x] **步骤 3：创建 `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    jwt_expires_minutes: int = 1440
    seed_admin_username: str = "admin"
    seed_admin_password: str
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
```

- [x] **步骤 4：创建 `backend/app/db.py`**

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
```

- [x] **步骤 5：创建 `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(title="球场预定管理系统 API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
```

（路由注册在后续任务逐个 `app.include_router(...)` 追加。）

- [x] **步骤 6：创建测试基建 `backend/tests/conftest.py`**

```python
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import Base, get_db
from app.main import app

TEST_DATABASE_URL = "postgresql+asyncpg://gym_app:你的口令@localhost:5432/gym_booking_test"


@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


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
```

- [x] **步骤 7：创建测试库并运行冒烟测试**

```bash
psql -U postgres -c "CREATE DATABASE gym_booking_test OWNER gym_app;"
python -m pytest tests/ -v
```

预期：0 个用例被收集（no tests ran），无错误。

- [x] **步骤 8：启动验证**

```bash
uvicorn app.main:app --reload
```

浏览器打开 `http://localhost:8000/docs` 确认 Swagger 可访问、`/healthz` 返回 `{"status":"ok"}`。

- [x] **步骤 9：Commit**

```bash
git status --short && git diff --stat
git add backend/requirements.txt backend/app/__init__.py backend/app/main.py backend/app/config.py backend/app/db.py backend/tests/
git commit -m "feat: fastapi skeleton with config db cors and test base"
```

### 任务 4：数据模型 + Alembic 迁移 + seed 管理员

**前置：** 任务 3

**文件：**
- 创建：`backend/app/models/__init__.py`、`backend/app/models/user.py`、`backend/app/models/application.py`、`backend/app/models/court.py`、`backend/app/models/booking.py`、`backend/app/seed.py`、`backend/alembic.ini`、`backend/alembic/`（`alembic init alembic` 生成）、`backend/tests/test_models.py`
- 修改：`backend/alembic/env.py`、`backend/tests/conftest.py`（增加 `db_session` fixture，见步骤 6）

- [x] **步骤 1：创建 4 个模型**（SQLAlchemy 2.0 `Mapped` 风格；字段与 SPEC 第 6 章一致）

```python
# app/models/user.py
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")  # user / venue_admin / admin
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

# app/models/application.py
class Application(Base):
    __tablename__ = "applications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # pending / approved / rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

# app/models/court.py
class Court(Base):
    __tablename__ = "courts"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # 羽毛球 / 篮球 / 网球 / 足球
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    open_time: Mapped[time] = mapped_column(Time, nullable=False)
    close_time: Mapped[time] = mapped_column(Time, nullable=False)
    slot_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)  # 60 / 120 / 180
    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

# app/models/booking.py
class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint("court_id", "date", "start_time", name="uq_booking_court_date_start"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    court_id: Mapped[int] = mapped_column(ForeignKey("courts.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="booked")  # booked / checked_in / cancelled
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

`models/__init__.py` 导出 4 个模型类，保证 `Base.metadata` 完整（Alembic 依赖）。

- [x] **步骤 2：初始化 Alembic 并改造 `env.py` 支持异步**

```bash
cd backend && alembic init alembic
```

修改 `backend/alembic/env.py`：`target_metadata = Base.metadata`；将 `sqlalchemy.url` 改为从 `app.config.settings.database_url` 读取，并使用异步引擎运行迁移：

```python
from app.config import settings
from app.db import Base
from app import models  # noqa: F401  确保模型注册

config.set_main_option("sqlalchemy.url", settings.database_url)

def run_migrations_offline(): ...
def run_migrations_online():
    connectable = async_engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()
```

- [x] **步骤 3：生成并执行初始迁移**

```bash
alembic revision --autogenerate -m "init users applications courts bookings"
alembic upgrade head
psql "postgresql://gym_app:你的口令@localhost:5432/gym_booking" -c "\d bookings"
```

预期：`\d bookings` 显示 `uq_booking_court_date_start` 唯一约束。

- [x] **步骤 4：创建 `backend/app/seed.py`（幂等：账号已存在则跳过）**

```python
async def seed_admin() -> None:
    async with SessionLocal() as db:
        existing = await db.scalar(select(User).where(User.username == settings.seed_admin_username))
        if existing:
            print(f"seed skipped: {settings.seed_admin_username} already exists")
            return
        db.add(User(username=settings.seed_admin_username,
                    password_hash=hash_password(settings.seed_admin_password),
                    role="admin"))
        await db.commit()
        print(f"seed created admin: {settings.seed_admin_username}")
```

`seed.py` 依赖 `app/security.py` 的 `hash_password`（在任务 5 实现；本任务先创建 `backend/app/security.py` 并实现 bcrypt 哈希函数，JWT 部分留待任务 5）。

- [x] **步骤 5：运行 seed 并验证**

```bash
python -m app.seed
psql "postgresql://gym_app:你的口令@localhost:5432/gym_booking" -c "SELECT id, username, role FROM users;"
```

预期：输出一行 `admin` / `admin`。再次运行 `python -m app.seed` 预期输出 `seed skipped`（幂等）。

- [x] **步骤 6：编写模型测试 `backend/tests/test_models.py`**

先在 `backend/tests/conftest.py` 增加 `db_session` fixture（从 `test_engine` 创建 sessionmaker 并 yield session，供模型级用例直连测试库使用），然后编写用例（pytest-asyncio）：
1. 创建 User → 默认 role 为 `user`
2. 创建 Booking 两条相同 `(court_id, date, start_time)` → 第二条 commit 抛 `IntegrityError`
3. `open_time` 晚于 `close_time` 的 Court 仅应用层拒绝（不依赖 DB）

- [x] **步骤 7：运行测试**

```bash
python -m pytest tests/ -v
```

预期：全部 PASS。

- [x] **步骤 8：Commit**

```bash
git status --short && git diff --stat
git add backend/app/models/ backend/app/seed.py backend/app/security.py backend/alembic.ini backend/alembic/ backend/tests/test_models.py
git commit -m "feat: models alembic migration and idempotent admin seed"
```

### 任务 5：认证（JWT + 注册 / 登录 / me）

**前置：** 任务 4

**文件：**
- 创建：`backend/app/schemas/auth.py`、`backend/app/routers/__init__.py`、`backend/app/routers/auth.py`、`backend/tests/test_auth.py`
- 修改：`backend/app/security.py`（补 JWT）、`backend/app/main.py`（注册路由）

- [x] **步骤 1：完善 `backend/app/security.py`**

```python
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expires_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "未登录")
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "登录已过期，请重新登录")
    user = await db.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在")
    return user  # 每次请求读库，角色变更即时生效


def require_role(*roles: str):
    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "无权限")
        return user
    return checker
```

- [x] **步骤 2：创建 `backend/app/schemas/auth.py`**

```python
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_]+$")
    password: str  # 校验器：长度≥6 且同时包含字母和数字

class LoginRequest(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: str
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class MeResponse(UserOut):
    application_status: str | None  # pending / approved / rejected / null（SPEC-D1）
```

- [x] **步骤 3：创建 `backend/app/routers/auth.py`**，端点：`POST /auth/register`（用户名重复 → 409「用户名已存在」）、`POST /auth/login`（用户名或密码错误统一返回 401「用户名或密码错误」）、`GET /auth/me`（含 `application_status` 查询，见 SPEC-D1）。

- [x] **步骤 4：注册路由到 `main.py`**，`app.include_router(auth_router, prefix="/auth", tags=["auth"])`。

- [x] **步骤 5：先写测试 `backend/tests/test_auth.py`**（TDD），用例：
1. 注册成功 → 201，响应含 UserOut 且无 password_hash
2. 重复用户名 → 409
3. 用户名含非法字符 / 过短 → 422
4. 密码纯数字 / 纯字母 / 过短 → 422
5. 登录成功 → 200，返回 `access_token`，user.role 为 `user`
6. 密码错误 → 401
7. `GET /auth/me` 无 token → 401；带 token → 200 且 username 匹配
8. 伪造 token → 401
9. 未注册时 `application_status` 为 null（SPEC-D1）

- [x] **步骤 6：运行测试**

```bash
python -m pytest tests/test_auth.py -v
```

预期：全部 PASS。

- [x] **步骤 7：Commit**

```bash
git status --short && git diff --stat
git add backend/app/security.py backend/app/schemas/auth.py backend/app/routers/ backend/app/main.py backend/tests/test_auth.py
git commit -m "feat: jwt auth with register login and me endpoints"
```

### 任务 6：场地管理员申请接口

**前置：** 任务 5

**文件：**
- 创建：`backend/app/schemas/application.py`、`backend/tests/test_application.py`
- 修改：`backend/app/routers/auth.py`（追加端点）

- [x] **步骤 1：先写测试**（TDD），用例：
1. 普通用户提交申请 → 201，`application_status` 变为 `pending`
2. 已有 pending 申请再提交 → 409「已有待审批申请」
3. 已有 approved 申请再提交 → 409「已是场地管理员」
4. 已驳回（rejected）后再提交 → 201（可重新申请，Q-14 基线）
5. 未登录提交 → 401；venue_admin / admin 提交 → 403

- [x] **步骤 2：实现 `POST /auth/apply-venue-admin`**：`require_role("user")`；按状态规则校验（上述 2/3/4）；创建 `Application(user_id, status="pending")`；返回 201。

- [x] **步骤 3：运行测试**

```bash
python -m pytest tests/test_application.py -v
```

预期：全部 PASS。

- [x] **步骤 4：Commit**

```bash
git status --short && git diff --stat
git add backend/app/routers/auth.py backend/app/schemas/application.py backend/tests/test_application.py
git commit -m "feat: venue admin application endpoint"
```

### 任务 7：球场公开接口（列表 / 筛选 / 详情 / booked-slots）

**前置：** 任务 5

**文件：**
- 创建：`backend/app/schemas/courts.py`（含 `COURT_TYPES` 枚举常量）、`backend/app/routers/courts.py`、`backend/tests/test_courts.py`
- 修改：`backend/app/main.py`

- [ ] **步骤 1：先写测试**（TDD），用例：
1. `GET /courts` 无数据 → 200 空列表
2. 造数后 `GET /courts` → 200，返回全部球场，字段含 id/name/type/price/open_time/close_time/slot_minutes
3. `GET /courts?type=篮球` → 仅返回篮球场
4. `GET /courts?price_min=50&price_max=100` → 价格区间内球场
5. `GET /courts/{id}` 存在 → 200；不存在 → 404
6. 创建类型非枚举值 → 422（`COURT_TYPES = ["羽毛球", "篮球", "网球", "足球"]`，字段校验）
7. `GET /courts/{id}/booked-slots?date=2026-09-25`：无预定 → 200 `[]`；有一条 09:00 预定 → `["09:00:00"]`；未带 date 参数 → 422

- [ ] **步骤 2：实现 `routers/courts.py`**：
  - `GET /courts`：可选 query 参数 `type` / `price_min` / `price_max`，`ORDER BY id`；公开访问
  - `GET /courts/{court_id}`：404 处理
  - `GET /courts/{court_id}/booked-slots?date=YYYY-MM-DD`：查该球场该日期所有 `start_time`，返回 `["09:00:00", ...]` 字符串列表（Q-19 / SPEC-2 基线）

- [ ] **步骤 3：运行测试**

```bash
python -m pytest tests/test_courts.py -v
```

预期：全部 PASS。

- [ ] **步骤 4：Commit**

```bash
git status --short && git diff --stat
git add backend/app/schemas/courts.py backend/app/routers/courts.py backend/app/main.py backend/tests/test_courts.py
git commit -m "feat: public courts endpoints with filters and booked slots"
```

### 任务 8：预定创建 + 防超订（核心任务）

**前置：** 任务 7

**文件：**
- 创建：`backend/app/schemas/bookings.py`、`backend/app/routers/bookings.py`、`backend/tests/test_bookings.py`、`backend/tests/test_overbooking.py`
- 修改：`backend/app/main.py`

- [ ] **步骤 1：先写防超订并发测试 `backend/tests/test_overbooking.py`**（TDD，核心验收 12.2）

```python
import asyncio

import pytest

@pytest.mark.asyncio
async def test_concurrent_same_slot_only_one_succeeds(client, user_token, court):
    payload = {"court_id": court.id, "date": str(TOMORROW), "start_time": "09:00:00"}
    async def book():
        return await client.post("/bookings", json=payload, headers=auth(user_token))
    r1, r2 = await asyncio.gather(book(), book())
    assert sorted([r1.status_code, r2.status_code]) == [201, 409]
```

- [ ] **步骤 2：先写功能测试 `backend/tests/test_bookings.py`**，用例：
1. 正常预定 → 201，`status=booked`、`price` 快照等于球场价格、`paid=false`
2. 球场不存在 → 404
3. venue_admin / admin 下单 → 403（Q-04 基线）
4. 未登录 → 401
5. date 超出今天起 7 天范围 → 409
6. start_time 不在开放时间内 / 未与 slot_minutes 对齐 / 时段尾部超出 close_time → 409
7. 当天已过时段 → 409「该时段已过」
8. 同一时段重复预定（顺序执行）→ 409「该时段已被预约」
9. 测试库 `SELECT COUNT(*)` 该 `(court_id, date, start_time)` 恒为 1

- [ ] **步骤 3：实现 `routers/bookings.py` 的 `POST /bookings`**

```python
@router.post("/bookings", status_code=201, response_model=BookingOut)
async def create_booking(
    payload: BookingCreate,
    user: User = Depends(require_role("user")),   # Q-04：仅普通用户
    db: AsyncSession = Depends(get_db),
):
    court = await db.get(Court, payload.court_id)
    if court is None:
        raise HTTPException(404, "球场不存在")
    validate_booking_request(court, payload)  # 日期范围 / 时段对齐 / 已过时段 → 409
    booking = Booking(user_id=user.id, court_id=court.id, date=payload.date,
                      start_time=payload.start_time, price=court.price)
    db.add(booking)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "该时段已被预约")
    await db.refresh(booking)
    return booking
```

`validate_booking_request` 规则（Q-16 / Q-20 / Q-09 / Q-10 基线）：`today <= date <= today + 6`；`open_time <= start_time` 且 `start_time + slot_minutes <= close_time`；`(start_time - open_time) % slot_minutes == 0`；`date == today 且 start_time <= 当前时间` → 409「该时段已过」。

- [ ] **步骤 4：运行测试**

```bash
python -m pytest tests/test_bookings.py tests/test_overbooking.py -v
```

预期：全部 PASS，并发用例稳定（可重复跑 3 次确认）。

- [ ] **步骤 5：Commit**

```bash
git status --short && git diff --stat
git add backend/app/schemas/bookings.py backend/app/routers/bookings.py backend/app/main.py backend/tests/test_bookings.py backend/tests/test_overbooking.py
git commit -m "feat: booking creation with db-level overbooking prevention"
```

### 任务 9：我的预定 + 取消

**前置：** 任务 8

**文件：**
- 创建：`backend/tests/test_my_bookings.py`
- 修改：`backend/app/routers/bookings.py`（追加端点）、`backend/app/schemas/bookings.py`（BookingOut 增加 `court_name`）

- [ ] **步骤 1：先写测试**（TDD），用例：
1. `GET /bookings/my` → 仅返回当前用户的预定，按 date DESC / start_time DESC 排序，含 `court_name`
2. 未登录 → 401
3. `DELETE /bookings/{id}` 本人未开始预定 → 200，`status` 变 `cancelled`（软取消，记录保留）
4. 取消他人预定 → 403
5. 预定不存在 → 404
6. 时段已开始（date+start_time ≤ 当前时间）→ 409「时段已开始，无法取消」（Q-06 基线）
7. 已核销预定取消 → 409；已取消预定再取消 → 409

- [ ] **步骤 2：实现**：
  - `GET /bookings/my`：`require_role("user")`，`Booking.user_id == current_user.id`，join Court 取名称
  - `DELETE /bookings/{booking_id}`：归属校验 → 403；状态校验（仅 `booked` 可取消）→ 409；时限校验（本机时区 `datetime.combine(date, start_time) <= now()`）→ 409；置 `status="cancelled"` 并 commit

- [ ] **步骤 3：运行测试**

```bash
python -m pytest tests/test_my_bookings.py -v
```

预期：全部 PASS。

- [ ] **步骤 4：Commit**

```bash
git status --short && git diff --stat
git add backend/app/routers/bookings.py backend/app/schemas/bookings.py backend/tests/test_my_bookings.py
git commit -m "feat: my bookings list and cancellation"
```

### 任务 10：venue_admin 球场维护 + 数据权限

**前置：** 任务 9

**文件：**
- 创建：`backend/app/routers/venue_admin.py`、`backend/app/routers/deps.py`（数据权限依赖）、`backend/tests/test_venue_admin_courts.py`
- 修改：`backend/app/main.py`

- [ ] **步骤 1：先写数据权限依赖 `routers/deps.py`**（设计提案，SPEC 8.3 要求统一依赖）

```python
async def get_owned_court(court_id: int, user: User = Depends(require_role("venue_admin", "admin")),
                          db: AsyncSession = Depends(get_db)) -> Court:
    court = await db.get(Court, court_id)
    if court is None:
        raise HTTPException(404, "球场不存在")
    if user.role != "admin" and court.owner_id != user.id:
        raise HTTPException(404, "球场不存在")   # 数据权限：越权一律按不存在处理，避免信息泄露
    return court
```

- [ ] **步骤 2：先写测试**（TDD），用例：
1. `GET /venue-admin/courts` → 仅返回自己名下的球场；无球场 → 空列表
2. venue_admin 访问他人球场 `GET/PUT` → 404（越权按不存在处理）
3. admin 访问任意球场 → 正常（不受 owner 限制）
4. `POST /venue-admin/courts` 合法数据 → 201，owner_id = 当前用户
5. `POST` 校验：类型非枚举 / slot_minutes 非 60/120/180 / open_time ≥ close_time / price ≤ 0 → 422
6. `PUT /venue-admin/courts/{id}` → 200 字段更新生效
7. 普通用户 / 未登录访问 → 403 / 401

- [ ] **步骤 3：实现 `routers/venue_admin.py`** 的球场端点：`GET /venue-admin/courts`（`owner_id == me` 过滤）、`POST /venue-admin/courts`（`CourtCreate` 校验）、`PUT /venue-admin/courts/{court_id}`（`get_owned_court` + 部分更新）。

- [ ] **步骤 4：运行测试**

```bash
python -m pytest tests/test_venue_admin_courts.py -v
```

预期：全部 PASS。

- [ ] **步骤 5：Commit**

```bash
git status --short && git diff --stat
git add backend/app/routers/venue_admin.py backend/app/routers/deps.py backend/app/main.py backend/tests/test_venue_admin_courts.py
git commit -m "feat: venue admin court management with owner scoping"
```

### 任务 11：venue_admin 预定管理（列表 / 日历 / 核销 / 取消）

**前置：** 任务 10

**文件：**
- 创建：`backend/tests/test_venue_admin_bookings.py`
- 修改：`backend/app/routers/venue_admin.py`、`backend/app/schemas/bookings.py`（管理视图响应模型：BookingOut + username）

- [ ] **步骤 1：先写测试**（TDD），用例：
1. `GET /venue-admin/bookings` → 仅返回自己球场下的预定，含 `username`；支持 `?court_id=` 与 `?date=` 筛选
2. 越权访问他人球场预定 → 空结果（过滤而非报错）
3. `GET /venue-admin/bookings/calendar?month=2026-09` → 返回当月预定（月视图数据源）；`?date=` 粒度日视图复用 `GET /venue-admin/bookings?date=`（Q-17 基线：月视图 + 日视图切换）
4. `POST /venue-admin/bookings/{id}/check-in` 对 `booked` → 200，status 变 `checked_in`
5. 重复核销 → 409「已核销」；核销已取消 → 409；核销他人球场预定 → 404
6. `DELETE /venue-admin/bookings/{id}` 取消自己球场下未开始预定 → 200；时限与状态规则同任务 9
7. 普通用户 / 未登录 → 403 / 401

- [ ] **步骤 2：实现**：预定查询一律 join Court 并按 `Court.owner_id == current_user.id` 过滤；核销与取消复用任务 9 的状态/时限规则；响应模型含 `username`（join User）。

- [ ] **步骤 3：运行测试**

```bash
python -m pytest tests/test_venue_admin_bookings.py -v
```

预期：全部 PASS。

- [ ] **步骤 4：Commit**

```bash
git status --short && git diff --stat
git add backend/app/routers/venue_admin.py backend/app/schemas/bookings.py backend/tests/test_venue_admin_bookings.py
git commit -m "feat: venue admin bookings check-in calendar and cancellation"
```

### 任务 12：admin 用户管理 + 申请审批

**前置：** 任务 11

**文件：**
- 创建：`backend/app/routers/admin.py`、`backend/tests/test_admin_users.py`
- 修改：`backend/app/main.py`

- [ ] **步骤 1：先写测试**（TDD），用例：
1. `GET /admin/users` → 200 全量用户列表，支持 `?role=user` 筛选；不含 password_hash
2. `PUT /admin/users/{id}/role` 设 `venue_admin` → 200，角色生效（该用户随后访问 venue-admin 接口成功）
3. role 传非法值 → 422
4. 修改自己的角色 → 409「不能修改自己的角色」（SPEC-D2）
5. `GET /admin/applications` → 200 申请列表，支持 `?status=pending` 筛选
6. `POST /admin/applications/{id}/approve` 对 pending → 200，申请变 approved，申请人角色变 `venue_admin`（同一事务）
7. `reject` 对 pending → 200，申请变 rejected，角色不变
8. 对非 pending 申请审批 → 409；申请不存在 → 404
9. 非 admin 访问全部返回 403 / 401

- [ ] **步骤 2：实现 `routers/admin.py`**：全部端点 `require_role("admin")`；审批动作在事务内完成「更新申请 + 升级角色」；Q-13 基线：仅查看 + 角色管理，不提供禁用/删除端点。

- [ ] **步骤 3：运行测试**

```bash
python -m pytest tests/test_admin_users.py -v
```

预期：全部 PASS。

- [ ] **步骤 4：Commit**

```bash
git status --short && git diff --stat
git add backend/app/routers/admin.py backend/app/main.py backend/tests/test_admin_users.py
git commit -m "feat: admin user management and application approval"
```

### 任务 13：admin 球场与预定全局管理

**前置：** 任务 12

**文件：**
- 创建：`backend/tests/test_admin_manage.py`
- 修改：`backend/app/routers/admin.py`

- [ ] **步骤 1：先写测试**（TDD），用例：
1. `GET /admin/courts` → 200 全部球场
2. `POST /admin/courts` 需 `owner_id`（须为 venue_admin 角色，否则 422）→ 201
3. `PUT /admin/courts/{id}` 修改任意球场 → 200
4. `DELETE /admin/courts/{id}` 无预定时 → 204；存在预定时 → 409「该球场存在预定记录，不可删除」（FK 保护）
5. `GET /admin/bookings` → 200 全部预定，含 username 与 court_name
6. `DELETE /admin/bookings/{id}` 取消任意预定 → 200（软取消，状态/时限规则同任务 9）
7. 非 admin → 403 / 401

- [ ] **步骤 2：实现**：admin 球场端点无 owner 过滤；删除球场前查 `bookings` 存在性；预定取消复用任务 9 规则。

- [ ] **步骤 3：运行测试**

```bash
python -m pytest tests/test_admin_manage.py -v
```

预期：全部 PASS。

- [ ] **步骤 4：Commit**

```bash
git status --short && git diff --stat
git add backend/app/routers/admin.py backend/tests/test_admin_manage.py
git commit -m "feat: admin global courts and bookings management"
```

### 任务 14：后端整体验收（PRD 10.1 / 10.2 / 10.4）

**前置：** 任务 13

- [ ] **步骤 1：全量测试**

```bash
cd backend && python -m pytest tests/ -v
```

预期：全部 PASS。

- [ ] **步骤 2：Swagger 与健康检查**：`uvicorn app.main:app --reload` 启动后打开 `http://localhost:8000/docs`，确认 5 个路由模块（auth / courts / bookings / venue_admin / admin）与 `/healthz` 全部可见。

- [ ] **步骤 3：curl 走通完整链路**（PRD 10.1）：

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"<.env 中 SEED_ADMIN_PASSWORD>"}' | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
curl -s http://localhost:8000/courts
curl -s -X POST http://localhost:8000/bookings -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"court_id":1,"date":"2026-09-25","start_time":"09:00:00"}'
```

预期：查场地返回 JSON；下单返回 403（admin 不可下单，Q-04 基线正确性自证）。再用注册的新用户走「注册 → 登录 → 查场地 → 下单 → 取消」。

- [ ] **步骤 4：防超订并发验收（PRD 10.2）**：运行任务 8 的并发测试并手工复核：

```bash
psql "postgresql://gym_app:你的口令@localhost:5432/gym_booking" -c "SELECT court_id, date, start_time, COUNT(*) FROM bookings GROUP BY 1,2,3 HAVING COUNT(*) > 1;"
psql "postgresql://gym_app:你的口令@localhost:5432/gym_booking" -c "\d bookings"
```

预期：第一条 SQL 输出 0 行；`\d` 显示 `uq_booking_court_date_start` 唯一约束。

- [ ] **步骤 5：Commit**（如验收中发现并修复了问题，提交修复；否则提交验收记录）

```bash
git status --short && git diff --stat
git add -A && git commit -m "test: backend acceptance verification"
```

## M4 前端

### 任务 15：前端初始化（create-next-app + lib 基础设施）

**前置：** 任务 1

**文件：**
- 创建：`frontend/`（脚手架生成）、`frontend/.env.local`、`frontend/src/lib/api.ts`、`frontend/src/lib/types.ts`、`frontend/src/lib/auth.ts`
- 修改：`frontend/src/app/layout.tsx`（全局导航与登录态）、`frontend/src/app/globals.css`（如需要）

- [ ] **步骤 1：生成脚手架**

```bash
cd /e/Dev/aicoding/demo260920-gym
npx create-next-app@latest frontend --typescript --app --tailwind --eslint --src-dir --import-alias "@/*" --use-npm
```

验证：`cd frontend && npm run dev` 后 http://localhost:3000 显示默认页；`npx tsc --noEmit` 无错误。

- [ ] **步骤 2：创建 `frontend/.env.local`**

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

- [ ] **步骤 3：创建 `frontend/src/lib/types.ts`**（与后端 schemas 对应：`User` / `Court` / `Booking` / `ApplicationStatus` / `TokenResponse` / `MeResponse`）。

- [ ] **步骤 4：创建 `frontend/src/lib/api.ts`**

```ts
const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
  if (res.status === 401 && typeof window !== "undefined" && !path.startsWith("/auth/login")) {
    localStorage.removeItem("token");
    window.location.href = `/login?next=${encodeURIComponent(window.location.pathname)}`;
    throw new ApiError(401, "未登录");
  }
  if (!res.ok) {
    let detail = `请求失败（${res.status}）`;
    try {
      const body = await res.json();
      if (body.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* 非 JSON 响应保持默认信息 */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json();
}
```

- [ ] **步骤 5：创建 `frontend/src/lib/auth.ts`**：`getToken` / `setToken` / `clearToken` / `isLoggedIn`（localStorage 键名 `token`）。

- [ ] **步骤 6：修改 `layout.tsx`**：顶部导航（场地列表 / 我的预定 / 个人中心 / 场地管理员 / 系统后台 / 登录注册或退出），按 `isLoggedIn` 与角色显示；`"use client"`。

- [ ] **步骤 7：验证**

```bash
npx tsc --noEmit && npm run build
```

预期：构建成功。浏览器确认导航与空页面可访问。

- [ ] **步骤 8：Commit**

```bash
git status --short && git diff --stat
git add frontend/
git commit -m "feat: next.js scaffold with api client types and auth helpers"
```

### 任务 16：注册 / 登录页

**前置：** 任务 15

**文件：**
- 创建：`frontend/src/app/login/page.tsx`、`frontend/src/app/register/page.tsx`

- [ ] **步骤 1：实现 `/register`**：用户名 + 密码 + 确认密码表单；客户端校验（长度/字符/密码规则）与后端 422 detail 展示；成功 → `router.push("/login")` 并提示注册成功。

- [ ] **步骤 2：实现 `/login`**：表单提交 `POST /auth/login`；成功 → `setToken` 并跳转 `next` 查询参数指向的页面（无则 `/venues`）；失败 → 展示 401 提示「用户名或密码错误」。

- [ ] **步骤 3：验证**

```bash
npx tsc --noEmit && npm run build && npm run dev
```

浏览器验收：注册新用户 → 自动到登录页 → 登录 → 跳转 `/venues`（此时无数据可显示空态，空态由任务 17 完成）；错误密码显示 401 提示；未登录访问 `/orders` → 被 api.ts 重定向到 `/login?next=/orders`。

- [ ] **步骤 4：Commit**

```bash
git status --short && git diff --stat
git add frontend/src/app/login frontend/src/app/register
git commit -m "feat: login and register pages"
```

### 任务 17：场地列表页（筛选）

**前置：** 任务 16

**文件：**
- 创建：`frontend/src/app/venues/page.tsx`

- [ ] **步骤 1：实现 `/venues`**：客户端组件，挂载时 `GET /courts`；卡片网格展示（名称 / 类型 / 价格 / 开放时间）；筛选控件：类型下拉（羽毛球/篮球/网球/足球 + 全部）、价格区间（min/max 输入），筛选变化即重新请求带 query 参数；空态文案「暂无场地」；加载与错误态（`ApiError.message` 展示）。

- [ ] **步骤 2：验证**

```bash
npx tsc --noEmit && npm run build
```

浏览器验收：后端启动且已有球场数据时（可先用任务 10 的接口或 seed 数据），列表正确展示；类型/价格筛选生效；空态与错误态正常。验收时若数据库无球场，先用场地管理员账号（admin 也可）创建测试球场。

- [ ] **步骤 3：Commit**

```bash
git status --short && git diff --stat
git add frontend/src/app/venues
git commit -m "feat: venue list page with filters"
```

### 任务 18：场地详情页

**前置：** 任务 17

**文件：**
- 创建：`frontend/src/app/venues/[courtId]/page.tsx`

- [ ] **步骤 1：实现 `/venues/[courtId]`**（SPEC-3 基线）：`GET /courts/{courtId}` 展示名称 / 类型 / 价格 / 开放时间 / 时段划分（由 open_time/close_time/slot_minutes 生成预览文本，如「09:00-22:00，每 60 分钟一节」）；「去预定」按钮 → `/book/[courtId]`；404 显示「场地不存在」。

- [ ] **步骤 2：验证**

```bash
npx tsc --noEmit && npm run build
```

浏览器验收：从列表页进入详情，字段齐全；「去预定」跳转正常；不存在的 id 显示 404 文案。

- [ ] **步骤 3：Commit**

```bash
git status --short && git diff --stat
git add frontend/src/app/venues
git commit -m "feat: venue detail page"
```

### 任务 19：预约页（时段网格，核心交互）

**前置：** 任务 18

**文件：**
- 创建：`frontend/src/app/book/[courtId]/page.tsx`

- [ ] **步骤 1：实现时段网格**：
  1. 日期选择器：今天起 7 天（今天 ≤ 选择 ≤ 今天+6，Q-20 基线），默认今天
  2. 网格生成（SPEC 9.2）：

```ts
function buildSlots(openTime: string, closeTime: string, slotMinutes: number): string[] {
  const [oh, om] = openTime.split(":").map(Number);
  const [ch, cm] = closeTime.split(":").map(Number);
  const open = oh * 60 + om;
  const close = ch * 60 + cm;
  const slots: string[] = [];
  for (let t = open; t + slotMinutes <= close; t += slotMinutes) {
    slots.push(`${String(Math.floor(t / 60)).padStart(2, "0")}:${String(t % 60).padStart(2, "0")}`);
  }
  return slots;
}
```

  3. 切换日期或初次加载时 `GET /courts/{courtId}/booked-slots?date=`，已订时段置灰禁用
  4. 当天已过时段置灰禁用（本机时间比较）
  5. 点击可订时段 → 确认弹窗（场地名 / 日期 / 时段 / 价格）→ 确认 → `POST /bookings`
  6. 成功 → 提示并跳转 `/orders`；409 → 提示 detail（「该时段已被预约」）并重新拉取 booked-slots 刷新置灰
  7. 未登录点击时段 → `/login?next=/book/[courtId]`（登录后回跳）

- [ ] **步骤 2：验证**

```bash
npx tsc --noEmit && npm run build
```

浏览器验收：网格数量与 `buildSlots` 一致；已订/已过时段灰色不可点；下单成功跳转「我的预定」；双浏览器窗口抢占同一时段，后确认者收到 409 提示且网格刷新为置灰（前端防超订场景）。

- [ ] **步骤 3：Commit**

```bash
git status --short && git diff --stat
git add frontend/src/app/book
git commit -m "feat: booking page with slot grid"
```

### 任务 20：我的预定页

**前置：** 任务 19

**文件：**
- 创建：`frontend/src/app/orders/page.tsx`

- [ ] **步骤 1：实现 `/orders`**：`GET /bookings/my` 列表（球场名 / 日期 / 时段 / 价格 / 状态徽章：已预定 / 已核销 / 已取消 / 已过期——由 `date`+`start_time` 与当前时间比较推导，不新增后端状态，Q-05 基线）；「取消」按钮：仅 `booked` 且未开始可点，二次确认后 `DELETE /bookings/{id}`，409 时展示 detail 并刷新列表。

- [ ] **步骤 2：验证**

```bash
npx tsc --noEmit && npm run build
```

浏览器验收：下单后列表可见；取消后状态徽章变「已取消」；已开始/已核销的预定取消按钮禁用。

- [ ] **步骤 3：Commit**

```bash
git status --short && git diff --stat
git add frontend/src/app/orders
git commit -m "feat: my orders page"
```

### 任务 21：个人中心（申请场地管理员）

**前置：** 任务 20

**文件：**
- 创建：`frontend/src/app/me/page.tsx`

- [ ] **步骤 1：实现 `/me`**：`GET /auth/me` 展示用户名与角色；普通用户显示申请区：无申请 →「申请成为场地管理员」按钮（`POST /auth/apply-venue-admin`）；`application_status` 为 pending → 显示「审批中」；rejected → 显示「已被驳回」+ 可重新申请按钮（Q-14 基线）；approved → 角色已变 venue_admin，申请入口隐藏并显示角色徽章。

- [ ] **步骤 2：验证**

```bash
npx tsc --noEmit && npm run build
```

浏览器验收：申请 → 状态变「审批中」；刷新页面状态保持；驳回后（由 admin 在任务 23 的操作触发）可重新申请。

- [ ] **步骤 3：Commit**

```bash
git status --short && git diff --stat
git add frontend/src/app/me
git commit -m "feat: profile page with venue admin application"
```

### 任务 22：场地管理员工作台

**前置：** 任务 21

**文件：**
- 创建：`frontend/src/app/venue-admin/page.tsx`

- [ ] **步骤 1：实现 `/venue-admin`**（三个 Tab）：
  1. **我的球场**：`GET /venue-admin/courts` 列表 + 新建表单（名称 / 类型下拉 / 价格 / 开放与关闭时间 / 时段粒度 60|120|180 下拉，Q-09 基线）+ 编辑（`POST` / `PUT`）；422 错误展示 detail
  2. **预定管理**：`GET /venue-admin/bookings`（可按日期筛选）列表展示 username / 球场 / 时段 / 状态；「核销」按钮（仅 booked，`POST .../check-in`）；「取消」按钮（规则同任务 20）；月视图 / 日视图切换（Q-17 基线）：月视图调 `GET /venue-admin/bookings/calendar?month=` 渲染月历格子（每日预定数 + 点击进入该日日视图），日视图即按 `?date=` 筛选的列表
  3. 非 venue_admin 访问 → 提示无权限（后端 403 由 api.ts 展示）

- [ ] **步骤 2：验证**

```bash
npx tsc --noEmit && npm run build
```

浏览器验收：新建球场后场地列表页可见（闭环）；用户下单后工作台列表出现预定；核销后状态变「已核销」；月视图显示当月预定并可切到日视图。

- [ ] **步骤 3：Commit**

```bash
git status --short && git diff --stat
git add frontend/src/app/venue-admin
git commit -m "feat: venue admin dashboard"
```

### 任务 23：系统管理员后台

**前置：** 任务 22

**文件：**
- 创建：`frontend/src/app/admin/page.tsx`

- [ ] **步骤 1：实现 `/admin`**（四个 Tab）：
  1. **用户管理**：`GET /admin/users` 列表 + 角色下拉修改（`PUT /admin/users/{id}/role`，Q-13 基线：仅查看 + 角色管理）
  2. **申请审批**：`GET /admin/applications?status=pending` 列表（含 username）+ 批准 / 驳回按钮（`POST .../approve` / `.../reject`）
  3. **球场管理**：`GET /admin/courts` 全部球场 + 编辑 / 删除（删除有预定球场时展示 409 detail）
  4. **预定管理**：`GET /admin/bookings` 全部预定 + 取消

- [ ] **步骤 2：验证**

```bash
npx tsc --noEmit && npm run build
```

浏览器验收：审批 pending 申请 → 对应用户 `/me` 显示 venue_admin 角色且工作台可访问；角色修改生效；球场删除在有预定时被拒绝。

- [ ] **步骤 3：Commit**

```bash
git status --short && git diff --stat
git add frontend/src/app/admin
git commit -m "feat: admin dashboard"
```

## M5 联调

### 任务 24：前后端联调 + 全流程验收（PRD 10.3）

**前置：** 任务 23

- [ ] **步骤 1：双端启动**：终端 A `cd backend && uvicorn app.main:app --reload`；终端 B `cd frontend && npm run dev`。确认前端请求不被 CORS 拦截（Network 面板无 CORS 错误）。

- [ ] **步骤 2：走查 PRD 10.3 全流程**：
  1. 注册 → 筛选场地 → 选场地 → 选时段 → 下单 → 我的预定 → 取消
  2. 普通用户申请场地管理员 → admin 审批通过 → 该用户新建球场 → 用户下单 → 场地管理员查看并核销
  3. 系统管理员后台管理用户、球场与预定
  4. 双窗口抢占同一时段 → 一个成功一个 409 提示且网格置灰
  5. 未登录点击时段 → 登录后回跳预约页

- [ ] **步骤 3：性能与兼容性抽查**（Q-24 / Q-25 基线）：Network 面板确认常规接口 < 1s；用最新版 Chrome/Edge 验收。

- [ ] **步骤 4：Commit**（联调中若修改了代码）

```bash
git status --short && git diff --stat
git add -A && git commit -m "chore: integration tuning and e2e acceptance"
```

### 任务 25：文档收尾与计划核对

**前置：** 任务 24

**文件：**
- 修改：`README.md`（seed 凭据说明与启动方式最终核对，Q-12 基线）、`docs/IMPLEMENTATION-PLAN.md`（勾选完成的步骤复选框）

- [ ] **步骤 1：核对 README**：启动方式与实际命令一致；补充「初始管理员账号来自 `backend/.env` 的 SEED_ADMIN_* 配置」说明。

- [ ] **步骤 2：核对本计划**：全部步骤复选框已勾选；与 PRD / SPEC 对照确认无遗漏需求（对照 PRD 10.1~10.4 验收清单逐项复核）。

- [ ] **步骤 3：Commit**

```bash
git status --short && git diff --stat
git add README.md docs/IMPLEMENTATION-PLAN.md
git commit -m "docs: finalize readme and plan checklist"
```
