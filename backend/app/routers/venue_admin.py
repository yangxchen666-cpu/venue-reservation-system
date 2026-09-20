from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.court import Court
from app.models.user import User
from app.routers.deps import get_owned_court
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
