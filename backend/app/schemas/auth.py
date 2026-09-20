from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_]+$")
    password: str  # 校验器：长度≥6 且同时包含字母和数字

    @field_validator("password")
    @classmethod
    def _validate_password(cls, v: str) -> str:
        if len(v) < 6 or not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("密码长度至少 6 位，且需同时包含字母和数字")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class MeResponse(UserOut):
    application_status: str | None  # pending / approved / rejected / null（SPEC-D1）
