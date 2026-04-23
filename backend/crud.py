from sqlalchemy import or_
from sqlalchemy.orm import Session

from .models import DialogInitiation, Like, Match, Profile, Rating, Skip, User


def get_user_by_telegram(db: Session, telegram_id: str) -> User | None:
    return db.query(User).filter(User.telegram_id == telegram_id).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, telegram_id: str, username: str | None) -> User:
    user = User(telegram_id=telegram_id, username=username)
    db.add(user)
    db.flush()

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


def get_profile_by_user_id(db: Session, user_id: int) -> Profile | None:
    return db.query(Profile).filter(Profile.user_id == user_id).first()


def profile_has_content(profile: Profile) -> bool:
    content_fields = (
        profile.age,
        profile.gender,
        profile.city,
        profile.interests,
        profile.bio,
        profile.photo_url,
        profile.preferred_gender,
        profile.preferred_age_min,
        profile.preferred_age_max,
        profile.preferred_city,
    )
    return any(value is not None for value in content_fields)


def create_profile(db: Session, user_id: int, profile_data: dict) -> Profile:
    profile = Profile(user_id=user_id, **profile_data)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update_profile(db: Session, profile: Profile, profile_data: dict) -> Profile:
    for field, value in profile_data.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile


def delete_profile(db: Session, profile: Profile) -> None:
    db.delete(profile)
    db.commit()


def get_rating(db: Session, user_id: int) -> Rating | None:
    return db.query(Rating).filter(Rating.user_id == user_id).first()


def get_match_between_users(db: Session, user_a_id: int, user_b_id: int) -> Match | None:
    return (
        db.query(Match)
        .filter(
            or_(
                (Match.user1_id == user_a_id) & (Match.user2_id == user_b_id),
                (Match.user1_id == user_b_id) & (Match.user2_id == user_a_id),
            )
        )
        .first()
    )


def create_match(db: Session, user_a_id: int, user_b_id: int) -> Match:
    user1_id, user2_id = sorted([user_a_id, user_b_id])
    existing_match = get_match_between_users(db, user1_id, user2_id)
    if existing_match:
        return existing_match

    match = Match(user1_id=user1_id, user2_id=user2_id)
    db.add(match)
    db.commit()
    db.refresh(match)
    return match


def get_like(db: Session, from_user_id: int, to_user_id: int) -> Like | None:
    return (
        db.query(Like)
        .filter(Like.from_user_id == from_user_id, Like.to_user_id == to_user_id)
        .first()
    )


def get_skip(db: Session, from_user_id: int, to_user_id: int) -> Skip | None:
    return (
        db.query(Skip)
        .filter(Skip.from_user_id == from_user_id, Skip.to_user_id == to_user_id)
        .first()
    )


def record_like(db: Session, from_user_id: int, to_user_id: int) -> tuple[Like, bool]:
    existing_skip = get_skip(db, from_user_id, to_user_id)
    if existing_skip:
        db.delete(existing_skip)
        db.flush()

    existing_like = get_like(db, from_user_id, to_user_id)
    if existing_like:
        db.commit()
        return existing_like, False

    like = Like(from_user_id=from_user_id, to_user_id=to_user_id)
    db.add(like)
    db.commit()
    db.refresh(like)
    return like, True


def record_skip(db: Session, from_user_id: int, to_user_id: int) -> tuple[Skip, bool]:
    existing_like = get_like(db, from_user_id, to_user_id)
    if existing_like:
        db.delete(existing_like)
        db.flush()

    existing_skip = get_skip(db, from_user_id, to_user_id)
    if existing_skip:
        db.commit()
        return existing_skip, False

    skip = Skip(from_user_id=from_user_id, to_user_id=to_user_id)
    db.add(skip)
    db.commit()
    db.refresh(skip)
    return skip, True


def is_mutual_like(db: Session, from_user_id: int, to_user_id: int) -> bool:
    return get_like(db, to_user_id, from_user_id) is not None


def get_matches_for_user(db: Session, user_id: int) -> list[Match]:
    return (
        db.query(Match)
        .filter(or_(Match.user1_id == user_id, Match.user2_id == user_id))
        .order_by(Match.created_at.desc())
        .all()
    )


def record_dialog_initiation(db: Session, match_id: int, from_user_id: int, to_user_id: int) -> DialogInitiation:
    dialog = DialogInitiation(
        match_id=match_id,
        from_user_id=from_user_id,
        to_user_id=to_user_id,
    )
    db.add(dialog)
    db.commit()
    db.refresh(dialog)
    return dialog
