# 球场预定管理系统 — 技术规格说明书（SPEC）

## 1. 文档信息

| 项目 | 内容 |
|---|---|
| 产品名称 | 球场预定管理系统（正式名称待确认，Q-01） |
| 文档版本 | v0.1 |
| 更新日期 | 2026-09-20 |
| 文档状态 | 草案 |
| 关联文档 | 产品需求文档：[PRD.md](PRD.md) v1.0；实施计划：[IMPLEMENTATION-PLAN.md](IMPLEMENTATION-PLAN.md) |

### 1.1 版本历史

| 版本 | 日期 | 变更说明 | 作者 |
|---|---|---|---|
| v0.1 | 2026-09-20 | 初稿：基于 PRD v1.0 与实施计划整理技术设计 | — |

### 1.2 文档定位与阅读约定

- 本 SPEC 是 PRD 的**技术实现规格**：在 PRD 需求之上补充系统架构、数据模型、API 契约与关键设计，作为研发实现依据。产品需求细节以 PRD 为准，本文不重复转述。
- PRD 中的 27 项待确认事项（Q-01 ~ Q-27）在本 SPEC 中**保持待确认状态，不冻结决策**。各章节以「待确认（Q-xx）」标注；第 11 章汇总表中「PRD 建议」一栏仅为参考，最终以 PRD 后续修订为准。
- 标记说明：「⚠ 冲突」表示 SPEC 自检发现的 PRD 内部矛盾，需产品侧裁定。
- 接口与字段级明细中标注「设计提案」的内容，为 SPEC 层面的技术建议，不属于产品需求冻结范围。

## 2. 范围概述

### 2.1 功能范围（摘要，详见 PRD 第 4、5 章）

| 角色 | 功能 |
|---|---|
| 游客 | 浏览场地列表、按类型/价格筛选、查看场地详情 |
| 普通用户（user） | 注册/登录、按日期+时段预定场地、查看/取消自己的预定、申请成为场地管理员 |
| 场地管理员（venue_admin） | 新建/维护自己名下的球场、查看自己球场预定（列表+日历）、核销/取消预定 |
| 系统管理员（admin） | 管理所有用户、审批场地管理员申请、管理所有球场与预定 |

### 2.2 非目标（PRD 4.2，不做）

- 在线支付：仅保留 mock 字段（Q-11），无真实支付
- 微信小程序端：仅 Web 端
- 营收结算 / 分成

### 2.3 用户故事与业务流程

用户故事与业务流程以 PRD 第 6、7 章为准（Q-27 待确认，其中「预定状态流转」待 Q-05 确定后以本 SPEC 9.3 为准）。

## 3. 系统架构

### 3.1 总体架构

前后端分离 + 单体后端 + 本机 PostgreSQL：

```
┌───────────────────────────┐
│  Next.js 15 前端           │  localhost:3000（App Router，TypeScript）
│  页面渲染 + 时段网格交互    │
└─────────────┬─────────────┘
              │ HTTP/JSON，Authorization: Bearer <JWT>
              │ CORS 仅放行 localhost:3000
┌─────────────▼─────────────┐
│  FastAPI 后端              │  localhost:8000（uvicorn，Swagger /docs）
│  routers / schemas /      │
│  models / security / seed │
└─────────────┬─────────────┘
              │ SQLAlchemy 2.x 异步（asyncpg 驱动）
┌─────────────▼─────────────┐
│  PostgreSQL 17 / 18        │  数据库 gym_booking
│  唯一约束 = 防超订最终保障  │
└───────────────────────────┘
```

约束：

- 前端仅通过后端 REST API 访问数据，禁止直连数据库
- API 契约以 FastAPI 自动生成的 OpenAPI 文档（http://localhost:8000/docs）为准；前端手写 TS 类型对接，不引入 openapi-generator
- 单机部署运行：`npm run dev` + `uvicorn` + 本机 PostgreSQL

### 3.2 组件职责

| 组件 | 职责 |
|---|---|
| `frontend/src/app` | 页面与交互：认证页、场地列表/筛选、预约时段网格、预定管理、管理工作台 |
| `backend/app/routers` | HTTP 路由与鉴权入口，按领域划分：auth / courts / bookings / venue_admin / admin |
| `backend/app/schemas` | Pydantic v2 请求/响应模型，输入输出边界 |
| `backend/app/models` + `alembic` | ORM 模型与数据库迁移，schema 的唯一事实来源 |
| `backend/app/security.py` | JWT 签发/校验、密码哈希 |
| `backend/app/seed.py` | 初始化系统管理员账号 |
| PostgreSQL | 数据持久化；防超订唯一约束的最终保障 |

## 4. 目录结构

```
demo260920-gym/
├── frontend/                    # Next.js 15 + TypeScript + Tailwind 4（create-next-app 生成）
│   └── src/app/                 # App Router 页面路由
│       ├── login/  register/    # 登录 / 注册
│       ├── venues/              # 场地列表与筛选
│       ├── book/[courtId]/      # 预约页（日期 + 时段网格）
│       ├── orders/              # 我的预定
│       ├── me/                  # 个人中心（含申请成为场地管理员）
│       ├── venue-admin/         # 场地管理员工作台
│       └── admin/               # 系统管理员后台
└── backend/
    ├── app/
    │   ├── main.py              # 应用入口 + CORS
    │   ├── config.py            # 配置读取（.env：数据库连接、JWT secret 等）
    │   ├── db.py                # SQLAlchemy async engine / session
    │   ├── models/              # User / Application / Court / Booking
    │   ├── schemas/             # Pydantic v2 请求/响应模型
    │   ├── routers/             # auth.py / courts.py / bookings.py / venue_admin.py / admin.py
    │   ├── seed.py              # 初始化系统管理员账号
    │   └── security.py          # JWT 签发与校验、bcrypt 密码哈希
    └── alembic/                 # 数据库迁移脚本
```

前端页面与后端路由模块映射（PRD 5.5）：

| 前端路由 | 功能 | 后端路由模块 |
|---|---|---|
| `/login` `/register` | 登录 / 注册 | `auth.py` |
| `/venues` | 场地列表与筛选 | `courts.py` |
| `/book/[courtId]` | 预约（日期 + 时段网格 + 下单） | `courts.py` + `bookings.py` |
| `/orders` | 我的预定 | `bookings.py` |
| `/me` | 个人中心（含申请成为场地管理员） | `auth.py` |
| `/venue-admin` | 场地管理员工作台 | `venue_admin.py` |
| `/admin` | 系统管理员后台 | `admin.py` |

前端约束：所有组件 / API 调用 / 页面使用 `.ts` / `.tsx`，禁止 `.js`。

## 5. 技术栈与版本

| 组件 | 版本 | 说明 |
|---|---|---|
| Node.js | ≥ 20 LTS | Next.js 15 要求 |
| Next.js | 15.5.x（App Router） | 已验证版本 `^15.5.9` |
| TypeScript | 5.x | 前端语言，必用 |
| React | 19.1.0 | 随 Next.js 15.5 |
| Tailwind CSS | 4.x（`@tailwindcss/postcss`） | |
| Python | 3.12+ | |
| FastAPI | ≥ 0.115（PyPI 最新稳定版） | 自带 Swagger 文档 |
| SQLAlchemy | 2.x | 异步，`asyncpg` 驱动 |
| Alembic | 1.x | 数据库迁移 |
| PostgreSQL | 17 或 18（本机安装；Q-23 待确认，PRD 建议以 17 为主、18 兼容） | 防超订依赖其事务 + 唯一约束 |
| 认证 | JWT（`PyJWT`）+ passlib/bcrypt | 三种角色：user / venue_admin / admin |

## 6. 数据模型

### 6.1 通用约定

- 表名用复数（SQLAlchemy 惯例）：`users` / `applications` / `courts` / `bookings`
- 主键 `id`：integer 自增
- 时间字段：`timestamptz`，默认 `now()`
- 金额：`numeric(10, 2)`
- 日期与时间分离存储（Q-16 待确认；PRD 建议：`date` 存日期，服务端按本机时区计算「当天」）
- 所有 schema 变更必须通过 Alembic 迁移，禁止手工改表

### 6.2 users — 用户

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | integer | PK | |
| username | varchar | UNIQUE, NOT NULL | 登录名（注册字段 Q-02 待确认；密码规则 Q-03 待确认） |
| password_hash | varchar | NOT NULL | bcrypt 哈希，禁止明文 |
| role | varchar | NOT NULL, default `'user'` | `user` / `venue_admin` / `admin` |
| created_at | timestamptz | NOT NULL, default now() | |

### 6.3 applications — 场地管理员申请

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | integer | PK | |
| user_id | integer | FK → users.id, NOT NULL | 申请人 |
| status | varchar | NOT NULL, default `'pending'` | `pending` / `approved` / `rejected` |
| created_at | timestamptz | NOT NULL, default now() | |
| reviewed_at | timestamptz | NULL | 审批时间 |

申请规则（Q-14 待确认；PRD 建议：被驳回后可重新申请，已通过后入口隐藏）。

### 6.4 courts — 球场

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | integer | PK | |
| owner_id | integer | FK → users.id, NOT NULL | 归属场地管理员，数据权限过滤依据 |
| name | varchar | NOT NULL | 球场名称 |
| type | varchar | NOT NULL | 场地类型枚举（Q-08 待确认；PRD 建议：羽毛球/篮球/网球/足球，seed 可扩展） |
| price | numeric(10,2) | NOT NULL | 一口价（Q-07 待确认；PRD 建议不做分时定价） |
| open_time | time | NOT NULL | 开放时间；Q-10 待确认（PRD 建议不支持跨日：`open_time` < `close_time`） |
| close_time | time | NOT NULL | 关闭时间 |
| slot_minutes | integer | NOT NULL | 时段长度（Q-09 待确认；⚠ 见 11.2 SPEC-1） |
| image_url | varchar | NULL | 预留字段，不做图片上传（Q-18 待确认） |

### 6.5 bookings — 预定

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | integer | PK | |
| user_id | integer | FK → users.id, NOT NULL | 预定人 |
| court_id | integer | FK → courts.id, NOT NULL | 球场 |
| date | date | NOT NULL | 预定日期 |
| start_time | time | NOT NULL | 时段开始时间 |
| status | varchar | 取值待确认 | 预定状态（Q-05 待确认；PRD 建议：`booked` / `checked_in` / `cancelled`） |
| price | numeric(10,2) | NULL | 下单时价格快照（Q-11 待确认） |
| paid | boolean | default false | mock 支付字段，无支付流程（Q-11 待确认） |
| created_at | timestamptz | NOT NULL, default now() | |

### 6.6 核心约束 — 防超订（已定需求，不属待确认）

1. **唯一约束**：`UNIQUE (court_id, date, start_time)` —— 同一球场同一日期同一开始时段最多一条预定记录

> **实施注记（联调修正）：** 约束按部分索引实现 `UNIQUE (court_id, date, start_time) WHERE status <> 'cancelled'`（索引名 `uq_booking_active_slot`，Alembic 迁移 `fe1d5b6b3537`）。软取消（记录保留）后该时段应重新可订，与 `GET /courts/{id}/booked-slots` 排除 cancelled 的语义一致；活跃预定（booked / checked_in）之间仍由数据库硬保证互斥。
2. **事务内插入**：创建预定在事务内执行 INSERT；捕获唯一约束冲突（IntegrityError）→ 回滚 → 返回 HTTP 409「该时段已被预约」
3. **禁止仅依赖应用层判断**：「先查询后插入」存在竞态窗口，不允许作为防超订手段；数据库层硬保证是唯一可接受实现
4. 并发下仅一个请求成功，其余请求明确失败（409）

### 6.7 实体关系

```
User 1 ─── N Application      （一个用户可多次申请）
User 1 ─── N Court            （Court.owner_id → 场地管理员）
User 1 ─── N Booking          （一个用户多条预定）
Court 1 ─── N Booking         （唯一约束保证同时段仅一条）
```

### 6.8 索引与查询

- 唯一约束 `(court_id, date, start_time)` 自带复合索引，前缀覆盖「按球场按日期」查询（预定列表 / booked-slots / 日历视图）
- 学习项目数据量小，暂不额外建索引；出现慢查询时再补（YAGNI）

## 7. API 契约

### 7.1 通用约定

- Base URL：`http://localhost:8000`；契约以 Swagger（`/docs`）为准
- 认证方式：请求头 `Authorization: Bearer <JWT>`（注册 / 登录 / 公开场地接口除外）
- 错误语义：401 未登录 / 403 无权限 / 404 资源不存在 / 409 时段冲突（防超订）/ 422 参数校验失败
- 错误响应体：FastAPI `HTTPException` 默认格式 `{"detail": "..."}`，前端按语义码处理
- 权限列依据 PRD 3.2 权限矩阵

### 7.2 接口清单（设计提案）

以下端点与路径为 SPEC 设计提案，最终以 Swagger 为准。

**`auth.py`：**

| 方法 | 路径 | 功能 | 权限 | 需求编号 |
|---|---|---|---|---|
| POST | `/auth/register` | 注册普通用户（字段 Q-02、密码规则 Q-03 待确认） | 公开 | F-AUTH-1 |
| POST | `/auth/login` | 登录，返回 JWT（有效期 Q-15 待确认） | 公开 | F-AUTH-2 |
| GET | `/auth/me` | 当前用户信息与角色 | 登录 | F-AUTH-3 |
| POST | `/auth/apply-venue-admin` | 提交场地管理员申请（重复性 Q-14 待确认） | user | F-VA-1 |

**`courts.py`：**

| 方法 | 路径 | 功能 | 权限 | 需求编号 |
|---|---|---|---|---|
| GET | `/courts` | 场地列表，支持 `type` / `price` 筛选（类型枚举 Q-08 待确认） | 公开 | F-USER-1/2 |
| GET | `/courts/{court_id}` | 场地详情 | 公开 | F-USER-3 |
| GET | `/courts/{court_id}/booked-slots?date=YYYY-MM-DD` | 指定日期已订时段列表，时段网格数据来源（Q-19 待确认：实施计划未列出，PRD 建议新增） | 公开 | F-USER-4 |

**`bookings.py`：**

| 方法 | 路径 | 功能 | 权限 | 需求编号 |
|---|---|---|---|---|
| POST | `/bookings` | 创建预定（事务 + 唯一约束，冲突返回 409） | user（Q-04 待确认：管理员是否可下单） | F-USER-4 |
| GET | `/bookings/my` | 我的预定列表 | user | F-USER-5 |
| DELETE | `/bookings/{booking_id}` | 取消自己的预定（时限 Q-06 待确认） | user（仅本人） | F-USER-6 |

**`venue_admin.py`（所有接口受数据权限约束，见 8.3）：**

| 方法 | 路径 | 功能 | 权限 | 需求编号 |
|---|---|---|---|---|
| GET | `/venue-admin/courts` | 我名下的球场列表 | venue_admin | F-VA-2/3 |
| POST | `/venue-admin/courts` | 新建球场 | venue_admin | F-VA-2 |
| PUT | `/venue-admin/courts/{court_id}` | 编辑自己名下的球场 | venue_admin | F-VA-3 |
| GET | `/venue-admin/bookings` | 我球场下的预定列表（支持按日期 / 球场筛选） | venue_admin | F-VA-4 |
| GET | `/venue-admin/bookings/calendar?month=` | 日历视图数据（粒度 Q-17 待确认） | venue_admin | F-VA-5 |
| POST | `/venue-admin/bookings/{booking_id}/check-in` | 核销（Q-26 待确认；PRD 建议：手动点击核销，不引入二维码） | venue_admin | F-VA-6 |
| DELETE | `/venue-admin/bookings/{booking_id}` | 取消自己球场下的预定 | venue_admin | F-VA-7 |

**`admin.py`：**

| 方法 | 路径 | 功能 | 权限 | 需求编号 |
|---|---|---|---|---|
| GET | `/admin/users` | 用户列表 | admin | F-ADMIN-1 |
| PUT | `/admin/users/{user_id}/role` | 修改角色（「用户管理」范围 Q-13 待确认；PRD 建议仅查看 + 角色管理，不做禁用/删除） | admin | F-ADMIN-1 |
| GET | `/admin/applications` | 申请列表 | admin | F-ADMIN-2 |
| POST | `/admin/applications/{application_id}/approve` | 批准申请（`pending` → `approved`，申请人升级 `venue_admin`） | admin | F-ADMIN-2 |
| POST | `/admin/applications/{application_id}/reject` | 驳回申请（`pending` → `rejected`） | admin | F-ADMIN-2 |
| GET | `/admin/courts` | 全部球场列表 | admin | F-ADMIN-3 |
| POST / PUT / DELETE | `/admin/courts/{court_id}` | 全局球场管理 | admin | F-ADMIN-3 |
| GET | `/admin/bookings` | 全部预定列表 | admin | F-ADMIN-4 |
| DELETE | `/admin/bookings/{booking_id}` | 取消任意预定 | admin | F-ADMIN-4 |

### 7.3 请求 / 响应模型要点（设计提案）

- `schemas/` 使用 Pydantic v2；参数校验失败由 FastAPI 统一返回 422
- 创建预定请求体：`{court_id, date, start_time}`；成功返回 201 + Booking；冲突返回 409「该时段已被预约」
- Booking 响应包含 `price` / `paid` mock 字段（Q-11 待确认）
- 登录响应：`{access_token, token_type: "bearer", user: {id, username, role}}`（设计提案）

## 8. 认证与授权

### 8.1 认证

- 密码使用 bcrypt 哈希存储（passlib），禁止明文；密码强度规则 Q-03 待确认
- 登录成功签发 JWT（`PyJWT`）；payload 设计提案：`sub`=user_id、`role`、`exp`；有效期 Q-15 待确认（PRD 建议：固定 24h，无刷新机制）
- 初始系统管理员由 `seed.py` 创建，不开放注册（F-AUTH-4）；凭据写入 backend `.env`，README 记录（Q-12 待确认）
- 后端鉴权依赖（设计提案）：`get_current_user` 校验 JWT；`require_role(...)` 校验角色，路由层统一使用，避免逐接口遗漏
- 前端（设计提案）：token 存 localStorage，请求统一携带 `Authorization: Bearer` 头；401 时引导重新登录

### 8.2 授权（角色矩阵）

以 PRD 3.2 权限矩阵为准。其中「场地管理员 / 系统管理员是否可下单」为 Q-04 待确认（PRD 建议：仅普通用户可下单，管理员端聚焦管理）。

### 8.3 数据权限（硬性规则）

- 场地管理员的所有查询与操作必须按 `Court.owner_id == current_user.id` 过滤（涉及 Booking 时经 `Booking.court_id` 关联 Court 校验），只能访问自己名下的球场与预定
- 系统管理员不受此限制
- 实现要求（设计提案）：在 `venue_admin.py` 路由层用统一的 FastAPI dependency 实现过滤，避免逐接口遗漏

## 9. 关键设计

### 9.1 防超订（核心正确性）

已定需求（PRD 9.1 / 6.6，不属待确认）：

1. `bookings` 表唯一约束 `UNIQUE (court_id, date, start_time)`（部分索引实现，见 6.6 实施注记）
2. 创建预定流程：
   1. 校验 `date` 在可预约范围内（范围 Q-20 待确认）、`start_time` 在 `open_time` ~ `close_time` 内且与 `slot_minutes` 对齐
   2. 事务内 INSERT；捕获 IntegrityError → 回滚 → 返回 409「该时段已被预约」
3. 禁止仅依赖应用层查询判断
4. 验收见 12.2

### 9.2 时段网格（前端预约页 `/book/[courtId]`）

1. 日期选择器：今天起 7 天（Q-20 待确认）
2. 网格生成：由 `open_time` / `close_time` / `slot_minutes` 计算（Q-09 待确认，⚠ 见 11.2 SPEC-1）
3. 置灰规则：已订时段（来自 `GET /courts/{id}/booked-slots?date=`）置灰不可点；当天已过时段置灰不可订
4. 交互：点击可订时段 → 确认弹窗（场地名 / 日期 / 时段 / 价格）→ 确认提交
5. 结果处理：成功 → 跳转「我的预定」；409 → 提示「该时段已被预约」并重新拉取该日期时段数据、刷新置灰
6. 未登录点击时段 → 跳转登录页，登录后回跳原场地页

### 9.3 预定状态机（Q-05 待确认）

PRD 建议参考（不冻结）：

```
booked ──核销──▶ checked_in
booked ──用户/管理员取消──▶ cancelled
```

- 过期未核销的预定展示为「已过期」，不新增状态
- 核销方式 Q-26 待确认（PRD 建议：场地管理员手动点击核销，不引入二维码）

### 9.4 取消规则

| 操作者 | 可取消范围 | 限制 |
|---|---|---|
| 普通用户 | 自己的预定 | 时限 Q-06 待确认（PRD 建议：仅时段开始前可取消） |
| 场地管理员 | 自己球场下的预定 | 数据权限 8.3 |
| 系统管理员 | 任意预定 | 无 |

## 10. 非功能需求

### 10.1 性能

Q-24 待确认（PRD 建议：常规页面与接口响应时间 < 1 秒，本机部署环境）。

### 10.2 安全（已定需求）

- 密码 bcrypt 哈希存储，禁止明文（PRD 9.2）
- JWT 认证 + 角色鉴权 + 数据权限（8.1 / 8.2 / 8.3）
- CORS 仅放行 `http://localhost:3000`
- 密钥与凭据（JWT secret、数据库口令、seed 管理员密码）写入 `.env`，`.gitignore` 排除，禁止提交代码库

### 10.3 兼容性

- 运行环境：Node.js ≥ 20 LTS、Python 3.12+、PostgreSQL 17 或 18
- 浏览器：Q-25 待确认（PRD 建议：现代浏览器最新两个大版本）

### 10.4 可用性

- 时段网格直观区分可订 / 已订状态（已订置灰）
- 操作结果有明确反馈（成功 / 失败提示，如 409 冲突提示「该时段已被预约」）
- 相关用户故事与流程细节 Q-27 待确认

## 11. 待确认事项汇总

### 11.1 PRD 待确认事项（Q-01 ~ Q-27）

状态：全部待确认，不冻结决策。以下「PRD 建议」仅为参考；「涉及章节」指向本 SPEC。

| 编号 | 事项 | PRD 建议（参考） | 涉及章节 |
|---|---|---|---|
| Q-01 | 产品正式名称 | 暂用「球场预定管理系统」 | 1 |
| Q-02 | 注册字段 | 仅用户名 + 密码（学习版） | 6.2、7.2 |
| Q-03 | 密码强度 / 找回密码 | 密码 ≥ 6 位，含字母和数字；不做找回（学习版） | 6.2、8.1 |
| Q-04 | 场地管理员 / 系统管理员是否可下单 | 仅普通用户可下单，管理员端聚焦管理 | 7.2、8.2 |
| Q-05 | 预定状态字段取值 | `booked` / `checked_in` / `cancelled`；过期展示「已过期」，不新增状态 | 6.5、9.3 |
| Q-06 | 取消预定时限 | 仅允许在时段开始前取消 | 7.2、9.4 |
| Q-07 | 价格计费口径 | 按场地一口价（`Court.price`），不做分时定价 | 6.4 |
| Q-08 | 场地类型枚举 | 羽毛球、篮球、网球、足球（seed 可扩展） | 6.4、7.2 |
| Q-09 | 时段粒度 | 60 / 120 / 180 分钟三档（默认 60）；⚠ 与 PRD 正文冲突，见 SPEC-1 | 6.4、9.2 |
| Q-10 | 跨日营业 | 不支持（`open_time` < `close_time`） | 6.4 |
| Q-11 | 支付 mock 字段呈现 | `Booking` 存 `price` / `paid`，UI 无支付步骤 | 6.5、7.3 |
| Q-12 | seed 管理员凭据管理 | 写入 backend `.env`，README 记录 | 8.1 |
| Q-13 | 「用户管理」范围 | 仅查看 + 角色管理；不做禁用 / 删除 | 7.2 |
| Q-14 | 管理员申请重复性 | 被驳回后可重新申请；已通过后入口隐藏 | 6.3、7.2 |
| Q-15 | JWT 有效期 | 固定有效期（如 24h），无刷新机制 | 8.1 |
| Q-16 | 时区与日期存储 | `date` 存日期；服务端按本机时区计算「当天」 | 6.1、6.5 |
| Q-17 | 日历视图粒度 | 月视图 + 日视图切换 | 7.2 |
| Q-18 | 球场图片 | 不做上传，可留 `image_url` 字段备用 | 6.4 |
| Q-19 | 时段网格数据来源接口 | 新增 `GET /courts/{id}/booked-slots?date=`（实施计划未列出） | 7.2、9.2 |
| Q-20 | 可预约日期范围 | 今天起 7 天 | 9.2 |
| Q-21 | 并发验收测试工具 | pytest + httpx 异步脚本（人工双 curl 备选） | 12.2 |
| Q-22 | 里程碑日期 | 未定 | 13 |
| Q-23 | PostgreSQL 版本取舍 | 以 17 为主，18 兼容 | 5 |
| Q-24 | 性能指标 | 常规接口 < 1 秒（本机环境） | 10.1 |
| Q-25 | 浏览器支持范围 | 现代浏览器最新两个大版本 | 10.3 |
| Q-26 | 核销方式 | 场地管理员手动点击核销，不引入二维码 | 7.2、9.3 |
| Q-27 | 用户故事与流程细节 | PRD 第 6、7 章为推导内容，待确认 | 2.3 |

### 11.2 SPEC 自检发现的新问题

| 编号 | 问题 | 说明 |
|---|---|---|
| SPEC-1 | ⚠ Q-09 与 PRD 正文冲突 | PRD 5.2 F-USER-4 写「默认 60 分钟 / 时段，可配 30 分钟」，Q-09 建议默认值为「60 / 120 / 180 分钟三档（默认 60）」；实施计划采用「默认 60，可配 30」。三个来源不一致，需产品侧裁定后统一（影响 6.4 `slot_minutes` 与 9.2 网格生成）。 |
| SPEC-2 | booked-slots 接口归属 | Q-19 已并入 7.2 接口提案（`GET /courts/{court_id}/booked-slots?date=`），响应结构待确认（建议：该日期已订时段的 `start_time` 列表）。 |
| SPEC-3 | 场地详情待确认项无编号 | PRD 5.2 F-USER-3「场地详情」标注待确认，但未归入 Q-01 ~ Q-27 任一项，需产品侧确认详情页字段范围（PRD 建议参考：名称 / 类型 / 价格 / 开放时间 / 时段划分）。 |

## 12. 验收标准

引用 PRD 第 10 章，验收执行前需先确认 Q-21（测试工具）。

### 12.1 后端验收

- [ ] `uvicorn app.main:app --reload` 启动后端，打开 `http://localhost:8000/docs` 确认 Swagger 文档可访问
- [ ] 用 curl 走通完整链路：注册 → 登录拿 token → 查场地 → 创建预约 → 取消

### 12.2 防超订验收（核心）

- [ ] 并发发送两个同一球场、同一日期、同一时段的预约请求，验证结果为一个 200、一个 409
- [ ] 数据库验证：`SELECT COUNT(*)` 查询该 `(court_id, date, start_time)` 的记录数恒为 1
- [ ] `psql` 检查 `bookings` 表唯一约束生效
- [ ] 测试工具 Q-21 待确认（PRD 建议：pytest + httpx 异步并发脚本，人工并行双 curl 备选）

### 12.3 前端验收

- [ ] `npm run dev` 启动前端，浏览器走通：注册 → 筛选场地 → 选场地 → 选时段 → 下单 → 我的预定 → 取消
- [ ] 普通用户申请成为场地管理员 → 系统管理员审批通过 → 场地管理员新建球场、查看并核销预定
- [ ] 系统管理员后台可管理用户、球场与预定

### 12.4 数据库验收

- [ ] `psql -d gym_booking` 抽查 `bookings` 数据与业务操作一致

## 13. 里程碑

按实施计划 5 个阶段顺序执行；时间节点 Q-22 待确认（未定）。

| 里程碑 | 内容 |
|---|---|
| M1 初始化 | `git init`、根目录 `.gitignore`、README 记录启动方式 |
| M2 数据库 | 安装本机 PostgreSQL（17/18），创建数据库 `gym_booking` |
| M3 后端 | FastAPI 骨架 → 模型 + Alembic 迁移 → auth → courts → bookings（防超订）→ venue_admin → admin |
| M4 前端 | Next.js 初始化 → 登录/注册页 → 场地列表 → 预约页 → 我的预定 → 个人中心 → 场地管理员工作台 → 系统管理员后台 |
| M5 联调 | 前后端 `.env` 配置、CORS 放行 `localhost:3000`、走通完整流程 |

## 14. 术语表

以 PRD 第 14 章为准，关键术语摘要：

| 中文 | 英文 | 说明 |
|---|---|---|
| 球场 | court | 可供预定的场地单元，由场地管理员维护 |
| 场地 | venue | 球场集合的概念（场地列表页 `/venues`） |
| 场地管理员 | venue_admin | 拥有自己名下球场维护权限的角色 |
| 系统管理员 | admin | 全局管理用户、球场与预定的角色 |
| 核销 | check-in | 用户到场后，管理员确认预定已使用 |
| 时段 | time slot | 按 `slot_minutes` 划分的可预定时间格 |
| 防超订 | overbooking prevention | 通过数据库唯一约束保证同一时段仅一条预定 |
