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
    court_name: str | None = None  # 列表接口 join Court 填充；创建响应为 null


class AdminBookingOut(BookingOut):
    """管理视图响应模型（venue_admin / admin）：BookingOut + username"""

    username: str
