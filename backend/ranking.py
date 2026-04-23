from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from .models import DialogInitiation, Like, Match, Profile, Rating, Skip


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def compute_level1_score(profile: Profile | None) -> float:
    if profile is None:
        return 0.0

    score = 0.0

    if profile.age is not None:
        score += 10
    if profile.gender:
        score += 10
    if profile.city:
        score += 10
    if profile.interests:
        score += 15
    if profile.bio:
        score += 10
    if profile.photo_url:
        score += 20
    if profile.preferred_gender:
        score += 10
    if profile.preferred_age_min is not None and profile.preferred_age_max is not None:
        score += 10
    if profile.preferred_city:
        score += 5

    return clamp(score)


def compute_level2_score(db: Session, user_id: int) -> float:
    likes_received = db.query(func.count(Like.id)).filter(Like.to_user_id == user_id).scalar() or 0
    skips_received = db.query(func.count(Skip.id)).filter(Skip.to_user_id == user_id).scalar() or 0
    matches_count = (
        db.query(func.count(Match.id))
        .filter(or_(Match.user1_id == user_id, Match.user2_id == user_id))
        .scalar()
        or 0
    )
    dialog_starts = (
        db.query(func.count(DialogInitiation.id))
        .filter(DialogInitiation.from_user_id == user_id)
        .scalar()
        or 0
    )

    recent_threshold = datetime.utcnow() - timedelta(days=7)
    evening_activity = (
        db.query(func.count(Like.id))
        .filter(Like.from_user_id == user_id, Like.created_at >= recent_threshold)
        .scalar()
        or 0
    ) + (
        db.query(func.count(Skip.id))
        .filter(Skip.from_user_id == user_id, Skip.created_at >= recent_threshold)
        .scalar()
        or 0
    ) + (
        db.query(func.count(DialogInitiation.id))
        .filter(
            DialogInitiation.from_user_id == user_id,
            DialogInitiation.created_at >= recent_threshold,
        )
        .scalar()
        or 0
    )

    total_reactions = likes_received + skips_received
    like_ratio = (likes_received / total_reactions) if total_reactions else 0.0

    score = 0.0
    score += min(likes_received * 8, 30)
    score += like_ratio * 25
    score += min(matches_count * 10, 20)
    score += min(dialog_starts * 10, 15)
    score += min(evening_activity * 2, 10)

    return clamp(score)


def recompute_rating(db: Session, user_id: int) -> Rating:
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    rating = db.query(Rating).filter(Rating.user_id == user_id).first()

    if not rating:
        rating = Rating(user_id=user_id)
        db.add(rating)
        db.flush()

    level1_score = compute_level1_score(profile)
    level2_score = compute_level2_score(db, user_id)
    final_score = clamp(level1_score * 0.5 + level2_score * 0.5)

    rating.level1_score = level1_score
    rating.level2_score = level2_score
    rating.final_score = final_score

    db.commit()
    db.refresh(rating)
    return rating


def recompute_many(db: Session, user_ids: list[int]) -> None:
    for user_id in sorted(set(user_ids)):
        recompute_rating(db, user_id)
