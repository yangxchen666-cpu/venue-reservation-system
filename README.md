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
