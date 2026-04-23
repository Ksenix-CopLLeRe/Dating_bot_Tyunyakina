from __future__ import annotations

import json

import redis
from sqlalchemy.orm import Session

from .config import REDIS_URL
from .models import Like, Match, Profile, Rating, Skip


QUEUE_SIZE = 10


redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def queue_key(user_id: int) -> str:
    return f"candidate_queue:{user_id}"


def current_key(user_id: int) -> str:
    return f"candidate_current:{user_id}"


def invalidate_candidate_cache(user_id: int) -> None:
    redis_client.delete(queue_key(user_id), current_key(user_id))


def get_current_candidate_id(user_id: int) -> int | None:
    value = redis_client.get(current_key(user_id))
    return int(value) if value is not None else None


def get_seen_user_ids(db: Session, user_id: int) -> set[int]:
    liked_ids = {
        row[0]
        for row in db.query(Like.to_user_id).filter(Like.from_user_id == user_id).all()
    }
    skipped_ids = {
        row[0]
        for row in db.query(Skip.to_user_id).filter(Skip.from_user_id == user_id).all()
    }
    matched_ids = {
        row[0]
        for row in db.query(Match.user1_id).filter(Match.user2_id == user_id).all()
    } | {
        row[0]
        for row in db.query(Match.user2_id).filter(Match.user1_id == user_id).all()
    }
    return liked_ids | skipped_ids | matched_ids | {user_id}


def compatibility_bonus(viewer: Profile, candidate: Profile) -> float:
    bonus = 0.0

    if viewer.preferred_gender and candidate.gender == viewer.preferred_gender:
        bonus += 15
    if viewer.preferred_city and candidate.city == viewer.preferred_city:
        bonus += 10
    if (
        viewer.preferred_age_min is not None
        and viewer.preferred_age_max is not None
        and candidate.age is not None
        and viewer.preferred_age_min <= candidate.age <= viewer.preferred_age_max
    ):
        bonus += 15

    if viewer.interests and candidate.interests:
        viewer_interests = {item.strip().lower() for item in viewer.interests.split(",") if item.strip()}
        candidate_interests = {item.strip().lower() for item in candidate.interests.split(",") if item.strip()}
        overlap = len(viewer_interests & candidate_interests)
        bonus += min(overlap * 4, 12)

    return bonus


def refill_candidate_queue(db: Session, user_id: int) -> list[int]:
    viewer = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not viewer:
        invalidate_candidate_cache(user_id)
        return []

    seen_user_ids = get_seen_user_ids(db, user_id)
    candidates = (
        db.query(Profile, Rating)
        .outerjoin(Rating, Rating.user_id == Profile.user_id)
        .filter(~Profile.user_id.in_(seen_user_ids))
        .filter(Profile.age.is_not(None))
        .filter(Profile.gender.is_not(None))
        .filter(Profile.city.is_not(None))
        .all()
    )

    ranked = sorted(
        candidates,
        key=lambda row: (
            (row[1].final_score if row[1] else 0.0) + compatibility_bonus(viewer, row[0]),
            row[0].updated_at.timestamp(),
        ),
        reverse=True,
    )

    candidate_ids = [profile.user_id for profile, _rating in ranked[:QUEUE_SIZE]]
    invalidate_candidate_cache(user_id)

    if candidate_ids:
        redis_client.rpush(queue_key(user_id), *candidate_ids)
        redis_client.set(current_key(user_id), candidate_ids[0])

    return candidate_ids


def get_or_load_current_candidate_id(db: Session, user_id: int) -> int | None:
    current = get_current_candidate_id(user_id)
    if current is not None:
        return current

    queue = redis_client.lrange(queue_key(user_id), 0, -1)
    if queue:
        current_id = int(queue[0])
        redis_client.set(current_key(user_id), current_id)
        return current_id

    candidate_ids = refill_candidate_queue(db, user_id)
    return candidate_ids[0] if candidate_ids else None


def consume_current_candidate(user_id: int) -> int | None:
    current = get_current_candidate_id(user_id)
    if current is None:
        queue = redis_client.lrange(queue_key(user_id), 0, -1)
        current = int(queue[0]) if queue else None

    if current is None:
        return None

    redis_client.lpop(queue_key(user_id))
    next_id = redis_client.lindex(queue_key(user_id), 0)

    if next_id is None:
        redis_client.delete(current_key(user_id))
    else:
        redis_client.set(current_key(user_id), next_id)

    return current


def queue_state(user_id: int) -> dict:
    return {
        "current_candidate_id": get_current_candidate_id(user_id),
        "remaining_cached_candidates": redis_client.llen(queue_key(user_id)),
    }
