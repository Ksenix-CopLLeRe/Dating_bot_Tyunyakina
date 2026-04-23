from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    telegram_id: str
    username: str | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: str
    username: str | None = None
    created_at: datetime


class RegistrationResponse(BaseModel):
    user: UserResponse
    created: bool
    message: str


class HealthResponse(BaseModel):
    status: str
    database: str
