from datetime import time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

COURT_TYPES = ["羽毛球", "篮球", "网球", "足球"]


class CourtCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    type: str
    price: Decimal
    open_time: time
    close_time: time
    slot_minutes: int = 60  # 60 / 120 / 180
    image_url: str | None = None

    @field_validator("type")
    @classmethod
    def _validate_type(cls, v: str) -> str:
        if v not in COURT_TYPES:
            raise ValueError(f"类型必须为 {'/'.join(COURT_TYPES)} 之一")
        return v

    @field_validator("price")
    @classmethod
    def _validate_price(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("价格必须大于 0")
        return v

    @field_validator("close_time")
    @classmethod
    def _validate_close_time(cls, v: time, info: ValidationInfo) -> time:
        # Q-10：不支持跨日营业，open_time < close_time
        if info.data.get("open_time") is not None and v <= info.data["open_time"]:
            raise ValueError("关闭时间必须晚于开放时间")
        return v

    @field_validator("slot_minutes")
    @classmethod
    def _validate_slot_minutes(cls, v: int) -> int:
        if v not in (60, 120, 180):
            raise ValueError("时段粒度必须为 60/120/180 分钟")
        return v


class CourtOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    price: Decimal
    open_time: time
    close_time: time
    slot_minutes: int
