from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import crud, schemas
from .database import Base, SessionLocal, engine


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Dating Bot Backend",
    description="Backend API for the first two stages of the dating bot project.",
    version="0.1.0",
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/", tags=["system"])
def root():
    return {
        "service": "dating-bot-backend",
        "status": "ok",
        "stage": "1-2",
    }


@app.get("/health", response_model=schemas.HealthResponse, tags=["system"])
def healthcheck(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return schemas.HealthResponse(status="ok", database="connected")


@app.post("/users/register", response_model=schemas.RegistrationResponse, tags=["users"])
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user, created = crud.get_or_create_user(db, user.telegram_id, user.username)
    message = "Пользователь зарегистрирован." if created else "Пользователь уже зарегистрирован."
    return schemas.RegistrationResponse(user=db_user, created=created, message=message)


@app.get(
    "/users/by-telegram/{telegram_id}",
    response_model=schemas.UserResponse,
    tags=["users"],
)
def get_user_by_telegram(telegram_id: str, db: Session = Depends(get_db)):
    user = crud.get_user_by_telegram(db, telegram_id)
    if not user:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Пользователь не найден.")
    return user
