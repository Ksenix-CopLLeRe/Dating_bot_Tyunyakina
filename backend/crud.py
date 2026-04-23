from sqlalchemy.orm import Session

from .models import Profile, Rating, User


def get_user_by_telegram(db: Session, telegram_id: str) -> User | None:
    return db.query(User).filter(User.telegram_id == telegram_id).first()


def create_user(db: Session, telegram_id: str, username: str | None) -> User:
    user = User(telegram_id=telegram_id, username=username)
    db.add(user)
    db.flush()

    db.add(Profile(user_id=user.id))
    db.add(Rating(user_id=user.id))

    db.commit()
    db.refresh(user)
    return user


def get_or_create_user(
    db: Session,
    telegram_id: str,
    username: str | None,
) -> tuple[User, bool]:
    user = get_user_by_telegram(db, telegram_id)
    if user:
        if username != user.username:
            user.username = username
            db.commit()
            db.refresh(user)
        return user, False

    return create_user(db, telegram_id, username), True
