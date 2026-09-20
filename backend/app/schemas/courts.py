from datetime import time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


class CourtOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    price: Decimal
    open_time: time
    close_time: time
    slot_minutes: int
