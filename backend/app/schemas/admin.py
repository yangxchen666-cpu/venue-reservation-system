from typing import Literal

from pydantic import BaseModel


class RoleUpdateRequest(BaseModel):
    role: Literal["user", "venue_admin", "admin"]
