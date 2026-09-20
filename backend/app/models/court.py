from datetime import time
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Court(Base):
    __tablename__ = "courts"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # 羽毛球 / 篮球 / 网球 / 足球
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    open_time: Mapped[time] = mapped_column(Time, nullable=False)
    close_time: Mapped[time] = mapped_column(Time, nullable=False)
    slot_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)  # 60 / 120 / 180
    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
