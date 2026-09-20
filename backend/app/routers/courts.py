from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.booking import Booking
from app.models.court import Court
from app.schemas.courts import CourtOut

router = APIRouter()


@router.get("/courts", response_model=list[CourtOut])
async def list_courts(
    type: str | None = None,
    price_min: Decimal | None = None,
    price_max: Decimal | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[Court]:
    query = select(Court).order_by(Court.id)
    if type is not None:
        query = query.where(Court.type == type)
    if price_min is not None:
        query = query.where(Court.price >= price_min)
    if price_max is not None:
        query = query.where(Court.price <= price_max)
    return list((await db.scalars(query)).all())


@router.get("/courts/{court_id}", response_model=CourtOut)
async def get_court(court_id: int, db: AsyncSession = Depends(get_db)) -> Court:
    court = await db.get(Court, court_id)
    if court is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "球场不存在")
    return court


@router.get("/courts/{court_id}/booked-slots", response_model=list[str])
async def booked_slots(
    court_id: int,
    date: date,
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    court = await db.get(Court, court_id)
    if court is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "球场不存在")
    # 已取消的预定不占用时段（Q-19 / SPEC-2：返回该日期已订时段）
    bookings = await db.scalars(
        select(Booking).where(
            Booking.court_id == court_id,
            Booking.date == date,
            Booking.status != "cancelled",
        )
    )
    return [booking.start_time.isoformat() for booking in bookings]
