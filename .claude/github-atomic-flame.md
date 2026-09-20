# 球场预定管理系统 — 实施计划

## Context

用户要做一个球场预定管理系统，定位为**学习/Demo/毕设**。已完成 GitHub 同类项目调研：

- SmartSportV / YuMQ / xiaoyouhui（273★/222★/193★）：微信小程序 + 微信云开发，国内主流路线但代码质量一般
- MeetHere（299★）：Spring Boot 2.2.2 + Thymeleaf，适合课设但技术栈旧
- BCMS（4★）：Next.js 15 + React 19 + FastAPI 类架构 + SignalR，技术栈最新最完整
- ep3-bs（215★）：PHP + Zend Framework 2，生产级老牌项目

**用户选定技术栈**：Next.js + Tailwind CSS（前端）/ FastAPI（后端）/ 本机 PostgreSQL（数据库）。

## 技术栈与版本

| 组件 | 版本 | 说明 |
|---|---|---|
| Node.js | ≥20 LTS | Next.js 15 要求 |
| Next.js | 15.5.x（App Router） | BCMS 验证版本 `^15.5.9` |
| TypeScript | 5.x（**前端语言，必用**） | BCMS 验证版本 `~5.9.2` |
| React | 19.1.0 | 随 Next.js 15.5 |
| Tailwind CSS | 4.x（`@tailwindcss/postcss`） | BCMS 验证版本 |
| Python | 3.12+ | |
| FastAPI | ≥0.115（装 PyPI 最新稳定版） | 自带 Swagger 文档 |
| SQLAlchemy | 2.x | 异步用 `asyncpg` 驱动 |
| Alembic | 1.x | 数据库迁移 |
| PostgreSQL | 17 或 18（本机安装） | 预约防超订依赖其事务+唯一约束 |
| 认证 | JWT（`PyJWT`）+ passlib/bcrypt | 三种角色：user / venue_admin / admin |

## 功能范围（学习版，适度裁剪）

- **普通用户**：注册/登录、查看场地信息、查询与筛选场地（按类型/价格等）、按日期+时段预定场地（时段网格）、查看自己的预定、取消预定
- **场地管理员**（普通用户提交申请，系统管理员审批后生效）：新建并维护自己名下的球场信息（名称/类型/价格/开放时间/时段）、查看并管理自己球场的预定情况（预定列表 + 日历视图、核销/取消）
- **系统管理员**：管理所有用户（含审批场地管理员申请）、管理所有球场、管理所有预定信息
- **不做**：在线支付（留 mock 字段）、微信小程序端、营收结算/分成

## 项目结构

```
e:\Dev\aicoding\demo260920-gym\
├── frontend/            # Next.js 15（TypeScript）+ Tailwind 4（create-next-app 生成）
│   └── src/app/         # /login /register /venues /book/[courtId] /orders /me /venue-admin /admin
└── backend/             # FastAPI
    ├── app/
    │   ├── main.py      # 应用入口 + CORS
    │   ├── config.py    # 数据库连接等配置（.env）
    │   ├── db.py        # SQLAlchemy async engine/session
    │   ├── models/      # User（含 role）/ Application（管理员申请审批）/ Court（含 owner_id）/ Booking（含唯一约束）
    │   ├── schemas/     # Pydantic v2 请求/响应模型
    │   ├── routers/     # auth.py / courts.py / bookings.py / venue_admin.py / admin.py
    │   ├── seed.py      # 初始化系统管理员账号
    │   └── security.py  # JWT 签发与校验、密码哈希
    └── alembic/         # 迁移脚本
```

## 关键设计

1. **防超订（核心）**：`bookings` 表对 `(court_id, date, start_time)` 建唯一约束；创建预约在事务内 INSERT，唯一冲突（IntegrityError）返回 409「该时段已被预约」。数据库层硬保证，不依赖应用层判断。
2. **时段模型**：`open_time`/`close_time` + `slot_minutes`（默认 60，可配 30），前端按此生成时段网格。
3. **API 契约**：FastAPI 自动生成 OpenAPI；前端先手写 TS 类型（学习项目，不引入 openapi-generator，后续可加）。
4. **认证与角色**：JWT Bearer + 角色字段（`role: user / venue_admin / admin`）。系统管理员由 seed 脚本创建初始账号；普通用户提交申请，系统管理员审批后升级为 venue_admin（`Application` 表：pending / approved / rejected）。
5. **数据权限**：场地管理员只能操作和查看自己名下的球场与预定（所有查询按 `Court.owner_id == current_user.id` 过滤）；系统管理员可管理全部用户、球场与预定。

## 实施步骤

1. 初始化：`git init`、根目录 `.gitignore`、README 记录启动方式
2. 安装本机 PostgreSQL（17/18），创建数据库 `gym_booking`
3. 后端：FastAPI 骨架 → SQLAlchemy 模型 + Alembic 初始迁移 → auth（注册/登录/JWT/申请成为场地管理员）→ courts 公开列表与查询筛选 → bookings（事务防超订 + 我的预定 + 取消）→ venue_admin 端点（新建维护自己球场、自己球场的预定列表/日历视图、核销）→ admin 端点（seed 初始管理员、用户管理、审批申请、全场与全预定管理）
4. 前端：`create-next-app --typescript`（TypeScript + App Router + Tailwind，所有组件/API 调用/页面均用 `.ts/.tsx`，禁止 `.js`）→ 登录/注册页 → 场地列表（查询筛选）→ 预约页（日期选择 + 时段网格，已订时段置灰）→ 我的预定 → 个人中心（申请成为场地管理员）→ 场地管理员工作台（球场新建与信息维护、预定查看与核销）→ 系统管理员后台（用户管理、申请审批、球场与预定管理）
5. 联调：前后端 `.env` 配置、CORS 放行 `localhost:3000`、走通完整流程

## 验证

- **后端**：`uvicorn app.main:app --reload` 启动，打开 `http://localhost:8000/docs` 确认 Swagger；curl 走通 注册 → 登录拿 token → 查场地 → 创建预约 → 取消
- **防超订**：并发发两个同一时段的预约请求，验证一个 200、一个 409；`psql` 检查唯一约束生效
- **前端**：`npm run dev`，浏览器走通 注册 → 筛选场地 → 选场地 → 选时段 → 下单 → 我的预定 → 取消；普通用户申请成为场地管理员 → 系统管理员审批 → 场地管理员新建球场、查看并核销预定；系统管理员后台可管理用户、球场与预定
- **数据库**：`psql -d gym_booking` 抽查 `bookings` 数据
