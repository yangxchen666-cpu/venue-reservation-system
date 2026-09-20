from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.booking import Booking
from app.models.court import Court
from app.models.user import User
from app.schemas.bookings import BookingCreate, BookingOut
from app.security import require_role

router = APIRouter()


def validate_booking_request(court: Court, payload: BookingCreate) -> None:
    # Q-16 / Q-20 / Q-09 / Q-10 基线规则
    today = date.today()
    if not (today <= payload.date <= today + timedelta(days=6)):
        raise HTTPException(status.HTTP_409_CONFLICT, "仅可预约今天起 7 天内的时段")
    open_min = court.open_time.hour * 60 + court.open_time.minute
    close_min = court.close_time.hour * 60 + court.close_time.minute
    start_min = payload.start_time.hour * 60 + payload.start_time.minute
    if start_min < open_min:
        raise HTTPException(status.HTTP_409_CONFLICT, "该时段不在开放时间内")
    if start_min + court.slot_minutes > close_min:
        raise HTTPException(status.HTTP_409_CONFLICT, "该时段超出关闭时间")
    if (start_min - open_min) % court.slot_minutes != 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "时段需与场地时段划分对齐")
    if payload.date == today and payload.start_time <= datetime.now().time():
        raise HTTPException(status.HTTP_409_CONFLICT, "该时段已过")


@router.post("/bookings", status_code=status.HTTP_201_CREATED, response_model=BookingOut)
async def create_booking(
    payload: BookingCreate,
    user: User = Depends(require_role("user")),  # Q-04：仅普通用户可下单
    db: AsyncSession = Depends(get_db),
) -> Booking:
    court = await db.get(Court, payload.court_id)
    if court is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "球场不存在")
    validate_booking_request(court, payload)
    booking = Booking(
        user_id=user.id,
        court_id=court.id,
        date=payload.date,
        start_time=payload.start_time,
        price=court.price,  # Q-11：下单时价格快照
    )
    db.add(booking)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "该时段已被预约")
    await db.refresh(booking)
    return booking
