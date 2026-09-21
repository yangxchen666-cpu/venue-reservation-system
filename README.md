# 球场预定管理系统

Next.js 15 + FastAPI + PostgreSQL 17，实现球场浏览、分时段预定、核销与全局管理的完整业务闭环。

## 目录结构

- `frontend/` — Next.js 15（App Router + TypeScript + Tailwind 4），页面与交互
- `backend/` — FastAPI + SQLAlchemy（异步）+ Alembic，REST API 与数据模型
- `docs/` — PRD.md（产品需求）/ SPEC.md（技术规格）/ IMPLEMENTATION-PLAN.md（实施计划）

## 启动方式

1. 数据库：本机 PostgreSQL 17，数据库 `gym_booking`（配置见 `backend/.env.example`）
2. 后端：`cd backend && python -m venv .venv && source .venv/Scripts/activate && pip install -r requirements.txt && alembic upgrade head && python -m app.seed && uvicorn app.main:app --reload`，Swagger 文档 http://localhost:8000/docs
3. 前端：`cd frontend && npm install && npm run dev`，访问 http://localhost:3000

## 账号说明

- 初始管理员账号由 `python -m app.seed` 创建，凭据来自 `backend/.env` 的 `SEED_ADMIN_USERNAME` / `SEED_ADMIN_PASSWORD`（默认用户名 `admin`，该文件不入库）
- 场地管理员不预置账号：普通用户注册后在「个人中心」申请，由系统管理员在「系统后台 → 申请审批」批准后生效
