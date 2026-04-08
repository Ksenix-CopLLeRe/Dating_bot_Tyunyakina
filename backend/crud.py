from sqlalchemy.orm import Session
from .models import User


def get_user_by_telegram(db: Session, telegram_id: str):
    return db.query(User).filter(User.telegram_id == telegram_id).first()


def create_user(db: Session, telegram_id: str, username: str):
    user = User(
        telegram_id=telegram_id,
        username=username
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user