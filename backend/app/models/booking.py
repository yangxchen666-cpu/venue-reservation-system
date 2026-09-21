from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, Time, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        # 防超订仅约束「活跃预定」：已取消的预定不占用时段，允许重新预定（与 booked-slots 语义一致）
        Index(
            "uq_booking_active_slot",
            "court_id",
            "date",
            "start_time",
            unique=True,
            postgresql_where=text("status <> 'cancelled'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    court_id: Mapped[int] = mapped_column(ForeignKey("courts.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="booked")  # booked / checked_in / cancelled
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
