from typing import Literal

from pydantic import BaseModel

from app.schemas.courts import CourtCreate


class RoleUpdateRequest(BaseModel):
    role: Literal["user", "venue_admin", "admin"]


class AdminCourtCreate(CourtCreate):
    """admin 建球场需指定 owner（须为 venue_admin，端点层校验）"""

    owner_id: int
