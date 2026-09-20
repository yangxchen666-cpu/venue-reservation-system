from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.application import Application
from app.models.user import User
from app.schemas.application import ApplicationOut
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.security import (
    create_access_token,
    get_current_user,
    hash_password,
    require_role,
    verify_password,
)

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> User:
    existing = await db.scalar(select(User).where(User.username == payload.username))
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "用户名已存在")
    user = User(username=payload.username, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "用户名已存在")
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user = await db.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户名或密码错误")
    return TokenResponse(access_token=create_access_token(user), user=UserOut.model_validate(user))


@router.get("/me", response_model=MeResponse)
async def me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    # SPEC-D1: 查询当前用户最新一条 Application 的 status，无申请记录则为 null
    application = await db.scalar(
        select(Application)
        .where(Application.user_id == user.id)
        .order_by(Application.id.desc())
        .limit(1)
    )
    return MeResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        created_at=user.created_at,
        application_status=application.status if application else None,
    )


@router.post("/apply-venue-admin", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
async def apply_venue_admin(
    user: User = Depends(require_role("user")),
    db: AsyncSession = Depends(get_db),
) -> Application:
    latest = await db.scalar(
        select(Application)
        .where(Application.user_id == user.id)
        .order_by(Application.id.desc())
        .limit(1)
    )
    if latest is not None:
        if latest.status == "pending":
            raise HTTPException(status.HTTP_409_CONFLICT, "已有待审批申请")
        if latest.status == "approved":
            raise HTTPException(status.HTTP_409_CONFLICT, "已是场地管理员")
    application = Application(user_id=user.id, status="pending")
    db.add(application)
    await db.commit()
    await db.refresh(application)
    return application
