from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    created_at: datetime
    reviewed_at: datetime | None


class AdminApplicationOut(ApplicationOut):
    """管理视图响应模型（admin）：ApplicationOut + user_id + username"""

    user_id: int
    username: str
