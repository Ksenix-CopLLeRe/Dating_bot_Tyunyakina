from pydantic import BaseModel


class UserCreate(BaseModel):
    telegram_id: str
    username: str | None = None


class UserResponse(BaseModel):
    id: int
    telegram_id: str
    username: str

    class Config:
        from_attributes = True