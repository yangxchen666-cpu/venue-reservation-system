from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class BookingCreate(BaseModel):
    court_id: int
    date: date
    start_time: time


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    court_id: int
    date: date
    start_time: time
    status: str
    price: Decimal | None
    paid: bool
    created_at: datetime
