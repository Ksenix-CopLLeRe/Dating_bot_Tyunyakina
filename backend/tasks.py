from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import timedelta
from typing import Iterable

from celery import Celery
from celery.schedules import crontab
from sqlalchemy.orm import Session

from . import cache
from .config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND, CELERY_TASK_ALWAYS_EAGER
from .database import SessionLocal
from .logging_config import configure_logging
from .models import Profile, User
from .ranking import recompute_many, recompute_rating


configure_logging()
logger = logging.getLogger(__name__)

celery_app = Celery(
    "dating_bot",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_always_eager=CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=True,
    broker_connection_timeout=2,
    task_publish_retry=False,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    beat_schedule={
        "recompute-all-ratings-every-5-minutes": {
            "task": "backend.tasks.recompute_all_ratings_task",
            "schedule": timedelta(minutes=5),
        },
        "warm-candidate-queues-every-5-minutes": {
            "task": "backend.tasks.warm_candidate_queues_task",
            "schedule": timedelta(minutes=5),
        },
        "worker-heartbeat-every-minute": {
            "task": "backend.tasks.worker_heartbeat_task",
            "schedule": crontab(minute="*"),
        },
    },
)


@contextmanager
def session_scope() -> Iterable[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@celery_app.task(name="backend.tasks.recompute_user_rating_task")
def recompute_user_rating_task(user_id: int) -> dict:
    with session_scope() as db:
        rating = recompute_rating(db, user_id)
        logger.info("rating.recomputed", extra={"user_id": user_id, "final_score": rating.final_score})
        return {
            "user_id": rating.user_id,
            "level1_score": rating.level1_score,
            "level2_score": rating.level2_score,
            "referral_score": rating.referral_score,
            "final_score": rating.final_score,
        }


@celery_app.task(name="backend.tasks.recompute_many_ratings_task")
def recompute_many_ratings_task(user_ids: list[int]) -> dict:
    unique_user_ids = sorted(set(user_ids))
    with session_scope() as db:
        recompute_many(db, unique_user_ids)
        logger.info("ratings.recomputed_many", extra={"user_ids": unique_user_ids})
    return {"updated_users": unique_user_ids}


@celery_app.task(name="backend.tasks.recompute_all_ratings_task")
def recompute_all_ratings_task() -> dict:
    with session_scope() as db:
        user_ids = [row[0] for row in db.query(User.id).all()]
        recompute_many(db, user_ids)
        logger.info("ratings.recomputed_all", extra={"count": len(user_ids)})
    return {"updated_count": len(user_ids)}


@celery_app.task(name="backend.tasks.refresh_candidate_queue_task")
def refresh_candidate_queue_task(user_id: int) -> dict:
    with session_scope() as db:
        candidate_ids = cache.refill_candidate_queue(db, user_id)
        logger.info(
            "candidate_queue.refreshed",
            extra={"user_id": user_id, "candidate_count": len(candidate_ids)},
        )
    return {"user_id": user_id, "candidate_count": len(candidate_ids)}


@celery_app.task(name="backend.tasks.warm_candidate_queues_task")
def warm_candidate_queues_task(limit: int = 50) -> dict:
    with session_scope() as db:
        user_ids = [row[0] for row in db.query(Profile.user_id).order_by(Profile.updated_at.desc()).limit(limit).all()]
        warmed = 0
        for user_id in user_ids:
            if cache.queue_state(user_id)["remaining_cached_candidates"] == 0:
                cache.refill_candidate_queue(db, user_id)
                warmed += 1
        logger.info("candidate_queue.warmed", extra={"checked": len(user_ids), "warmed": warmed})
    return {"checked": len(user_ids), "warmed": warmed}


@celery_app.task(name="backend.tasks.worker_heartbeat_task")
def worker_heartbeat_task() -> dict:
    cache.redis_client.set("celery:worker:heartbeat", "ok", ex=90)
    return {"status": "ok"}
