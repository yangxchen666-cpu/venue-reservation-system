from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.booking import Booking
from app.models.court import Court
from app.models.user import User
from app.routers.deps import get_owned_booking, get_owned_court
from app.schemas.bookings import AdminBookingOut, BookingOut
from app.schemas.courts import CourtCreate, CourtOut
from app.security import require_role

router = APIRouter()


@router.get("/venue-admin/courts", response_model=list[CourtOut])
async def list_my_courts(
    user: User = Depends(require_role("venue_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> list[Court]:
    query = select(Court).order_by(Court.id)
    if user.role != "admin":
        query = query.where(Court.owner_id == user.id)
    return list((await db.scalars(query)).all())


@router.post("/venue-admin/courts", response_model=CourtOut, status_code=status.HTTP_201_CREATED)
async def create_court(
    payload: CourtCreate,
    user: User = Depends(require_role("venue_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> Court:
    court = Court(
        owner_id=user.id,
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


@router.put("/venue-admin/courts/{court_id}", response_model=CourtOut)
async def update_court(
    court_id: int,
    payload: CourtCreate,
    court: Court = Depends(get_owned_court),
    db: AsyncSession = Depends(get_db),
) -> Court:
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


def _fill_admin_booking_out(booking: Booking, court_name: str, username: str) -> AdminBookingOut:
    base = BookingOut.model_validate(booking)
    data = base.model_dump(exclude={"court_name"})
    return AdminBookingOut(**data, court_name=court_name, username=username)


async def _load_admin_booking_out(db: AsyncSession, booking: Booking) -> AdminBookingOut:
    court = await db.get(Court, booking.court_id)
    user = await db.get(User, booking.user_id)
    return _fill_admin_booking_out(booking, court.name, user.username)


def _bookings_query():
    return (
        select(Booking, Court.name, User.username)
        .join(Court, Booking.court_id == Court.id)
        .join(User, Booking.user_id == User.id)
    )


@router.get("/venue-admin/bookings", response_model=list[AdminBookingOut])
async def list_venue_bookings(
    court_id: int | None = None,
    date: date | None = None,
    user: User = Depends(require_role("venue_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> list[AdminBookingOut]:
    query = _bookings_query()
    if user.role != "admin":
        # 数据权限：仅返回自己球场下的预定
        query = query.where(Court.owner_id == user.id)
    if court_id is not None:
        query = query.where(Booking.court_id == court_id)
    if date is not None:
        query = query.where(Booking.date == date)
    query = query.order_by(Booking.date.desc(), Booking.start_time.desc())
    rows = (await db.execute(query)).all()
    return [_fill_admin_booking_out(booking, court_name, username) for booking, court_name, username in rows]


@router.get("/venue-admin/bookings/calendar", response_model=list[AdminBookingOut])
async def venue_bookings_calendar(
    month: str,
    user: User = Depends(require_role("venue_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> list[AdminBookingOut]:
    # Q-17 基线：月视图数据源，month 形如 YYYY-MM
    try:
        first_day = datetime.strptime(month, "%Y-%m").date()
    except ValueError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "month 格式应为 YYYY-MM")
    if first_day.month == 12:
        next_month_first = date(first_day.year + 1, 1, 1)
    else:
        next_month_first = date(first_day.year, first_day.month + 1, 1)
    query = _bookings_query().where(
        Booking.date >= first_day, Booking.date < next_month_first
    )
    if user.role != "admin":
        query = query.where(Court.owner_id == user.id)
    query = query.order_by(Booking.date, Booking.start_time)
    rows = (await db.execute(query)).all()
    return [_fill_admin_booking_out(booking, court_name, username) for booking, court_name, username in rows]


@router.post("/venue-admin/bookings/{booking_id}/check-in", response_model=AdminBookingOut)
async def check_in_booking(
    booking: Booking = Depends(get_owned_booking),
    db: AsyncSession = Depends(get_db),
) -> AdminBookingOut:
    if booking.status == "checked_in":
        raise HTTPException(status.HTTP_409_CONFLICT, "已核销")
    if booking.status != "booked":
        raise HTTPException(status.HTTP_409_CONFLICT, "当前状态不可核销")
    booking.status = "checked_in"
    await db.commit()
    await db.refresh(booking)
    return await _load_admin_booking_out(db, booking)


@router.delete("/venue-admin/bookings/{booking_id}", response_model=AdminBookingOut)
async def cancel_venue_booking(
    booking: Booking = Depends(get_owned_booking),
    db: AsyncSession = Depends(get_db),
) -> AdminBookingOut:
    # 状态与时限规则同任务 9（用户侧取消）
    if booking.status != "booked":
        raise HTTPException(status.HTTP_409_CONFLICT, "当前状态不可取消")
    slot_start = datetime.combine(booking.date, booking.start_time)
    if slot_start <= datetime.now():
        raise HTTPException(status.HTTP_409_CONFLICT, "时段已开始，无法取消")
    booking.status = "cancelled"
    await db.commit()
    await db.refresh(booking)
    return await _load_admin_booking_out(db, booking)
