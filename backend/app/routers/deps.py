from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.court import Court
from app.models.user import User
from app.security import require_role


async def get_owned_court(
    court_id: int,
    user: User = Depends(require_role("venue_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> Court:
    court = await db.get(Court, court_id)
    if court is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "球场不存在")
    if user.role != "admin" and court.owner_id != user.id:
        # 数据权限：越权一律按不存在处理，避免信息泄露（SPEC 8.3）
        raise HTTPException(status.HTTP_404_NOT_FOUND, "球场不存在")
    return court
