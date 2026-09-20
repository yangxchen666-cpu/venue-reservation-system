from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.application import Application
from app.models.user import User
from app.schemas.admin import RoleUpdateRequest
from app.schemas.application import AdminApplicationOut, ApplicationOut
from app.schemas.auth import UserOut
from app.security import require_role

router = APIRouter()

# Q-13 基线：用户管理仅「查看 + 角色管理」，不提供禁用/删除端点


def _fill_admin_application_out(application: Application, username: str) -> AdminApplicationOut:
    base = ApplicationOut.model_validate(application)
    return AdminApplicationOut(
        **base.model_dump(), user_id=application.user_id, username=username
    )


@router.get("/admin/users", response_model=list[UserOut])
async def list_users(
    role: str | None = None,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> list[User]:
    query = select(User).order_by(User.id)
    if role is not None:
        query = query.where(User.role == role)
    return list((await db.scalars(query)).all())


@router.put("/admin/users/{user_id}/role", response_model=UserOut)
async def update_user_role(
    user_id: int,
    payload: RoleUpdateRequest,
    current: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> User:
    # SPEC-D2：目标为本人时拒绝，防止管理员锁死自己
    if user_id == current.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "不能修改自己的角色")
    target = await db.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "用户不存在")
    target.role = payload.role
    await db.commit()
    await db.refresh(target)
    return target


@router.get("/admin/applications", response_model=list[AdminApplicationOut])
async def list_applications(
    status: str | None = None,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> list[AdminApplicationOut]:
    query = (
        select(Application, User.username)
        .join(User, Application.user_id == User.id)
        .order_by(Application.id)
    )
    if status is not None:
        query = query.where(Application.status == status)
    rows = (await db.execute(query)).all()
    return [_fill_admin_application_out(application, username) for application, username in rows]


async def _review_application(
    application_id: int, db: AsyncSession, approve: bool
) -> AdminApplicationOut:
    application = await db.get(Application, application_id)
    if application is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "申请不存在")
    if application.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "该申请已处理")
    target = await db.get(User, application.user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "申请人不存在")
    application.status = "approved" if approve else "rejected"
    application.reviewed_at = datetime.now(timezone.utc)
    if approve:
        target.role = "venue_admin"
    await db.commit()  # 同一事务：更新申请 + 升级角色
    await db.refresh(application)
    return _fill_admin_application_out(application, target.username)


@router.post("/admin/applications/{application_id}/approve", response_model=AdminApplicationOut)
async def approve_application(
    application_id: int,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> AdminApplicationOut:
    return await _review_application(application_id, db, approve=True)


@router.post("/admin/applications/{application_id}/reject", response_model=AdminApplicationOut)
async def reject_application(
    application_id: int,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> AdminApplicationOut:
    return await _review_application(application_id, db, approve=False)
