from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.application import Application
from app.models.booking import Booking
from app.models.court import Court
from app.models.user import User
from app.schemas.admin import AdminCourtCreate, RoleUpdateRequest
from app.schemas.application import AdminApplicationOut, ApplicationOut
from app.schemas.auth import UserOut
from app.schemas.bookings import AdminBookingOut, BookingOut
from app.schemas.courts import CourtCreate, CourtOut
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


# ---- 球场全局管理 ----

# 与 venue_admin 的 _fill_admin_booking_out 逻辑一致（admin 无 owner 过滤，故独立一份）


def _fill_admin_booking_out(booking: Booking, court_name: str, username: str) -> AdminBookingOut:
    base = BookingOut.model_validate(booking)
    data = base.model_dump(exclude={"court_name"})
    return AdminBookingOut(**data, court_name=court_name, username=username)


async def _load_admin_booking_out(db: AsyncSession, booking: Booking) -> AdminBookingOut:
    court = await db.get(Court, booking.court_id)
    user = await db.get(User, booking.user_id)
    return _fill_admin_booking_out(booking, court.name, user.username)


@router.get("/admin/courts", response_model=list[CourtOut])
async def list_all_courts(
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> list[Court]:
    query = select(Court).order_by(Court.id)
    return list((await db.scalars(query)).all())


@router.post("/admin/courts", response_model=CourtOut, status_code=status.HTTP_201_CREATED)
async def create_court_global(
    payload: AdminCourtCreate,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> Court:
    owner = await db.get(User, payload.owner_id)
    if owner is None or owner.role != "venue_admin":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "owner_id 必须为场地管理员")
    court = Court(
        owner_id=payload.owner_id,
        name=payload.name,
        type=payload.type,
        price=payload.price,
        open_time=payload.open_time,
        close_time=payload.close_time,
        slot_minutes=payload.slot_minutes,
        image_url=payload.image_url,
    )
    db.add(court)
    await db.commit()
    await db.refresh(court)
    return court


@router.put("/admin/courts/{court_id}", response_model=CourtOut)
async def update_court_global(
    court_id: int,
    payload: CourtCreate,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> Court:
    court = await db.get(Court, court_id)
    if court is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "球场不存在")
    court.name = payload.name
    court.type = payload.type
    court.price = payload.price
    court.open_time = payload.open_time
    court.close_time = payload.close_time
    court.slot_minutes = payload.slot_minutes
    court.image_url = payload.image_url
    await db.commit()
    await db.refresh(court)
    return court


@router.delete("/admin/courts/{court_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_court_global(
    court_id: int,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> None:
    court = await db.get(Court, court_id)
    if court is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "球场不存在")
    existing = await db.scalar(select(Booking.id).where(Booking.court_id == court_id).limit(1))
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "该球场存在预定记录，不可删除")
    await db.delete(court)
    try:
        await db.commit()
    except IntegrityError:
        # 竞态兜底：检查与删除之间出现了新预定，FK 约束拒绝删除
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "该球场存在预定记录，不可删除")


# ---- 预定全局管理 ----


@router.get("/admin/bookings", response_model=list[AdminBookingOut])
async def list_all_bookings(
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> list[AdminBookingOut]:
    query = (
        select(Booking, Court.name, User.username)
        .join(Court, Booking.court_id == Court.id)
        .join(User, Booking.user_id == User.id)
        .order_by(Booking.date.desc(), Booking.start_time.desc())
    )
    rows = (await db.execute(query)).all()
    return [_fill_admin_booking_out(booking, court_name, username) for booking, court_name, username in rows]


@router.delete("/admin/bookings/{booking_id}", response_model=AdminBookingOut)
async def cancel_booking_global(
    booking_id: int,
    _: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> AdminBookingOut:
    # 软取消，状态/时限规则同任务 9（用户侧取消），无 owner 过滤
    booking = await db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "预定不存在")
    if booking.status != "booked":
        raise HTTPException(status.HTTP_409_CONFLICT, "当前状态不可取消")
    slot_start = datetime.combine(booking.date, booking.start_time)
    if slot_start <= datetime.now():
        raise HTTPException(status.HTTP_409_CONFLICT, "时段已开始，无法取消")
    booking.status = "cancelled"
    await db.commit()
    await db.refresh(booking)
    return await _load_admin_booking_out(db, booking)
