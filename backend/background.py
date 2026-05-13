from __future__ import annotations

import logging
from typing import Any

from celery import Task
from celery.exceptions import CeleryError
from kombu.exceptions import OperationalError

from .tasks import (
    recompute_many_ratings_task,
    recompute_user_rating_task,
    refresh_candidate_queue_task,
)


logger = logging.getLogger(__name__)


def enqueue_task(task: Task, *args: Any, **kwargs: Any) -> bool:
    try:
        task.apply_async(args=args, kwargs=kwargs)
    except (CeleryError, OperationalError, OSError) as exc:
        logger.warning(
            "celery.enqueue_failed",
            extra={"task": task.name, "error": str(exc)},
        )
        return False
    return True


def schedule_rating_refresh(user_ids: list[int]) -> bool:
    unique_user_ids = sorted(set(user_ids))
    if not unique_user_ids:
        return True
    if len(unique_user_ids) == 1:
        return enqueue_task(recompute_user_rating_task, unique_user_ids[0])
    return enqueue_task(recompute_many_ratings_task, unique_user_ids)


def schedule_queue_refresh(user_id: int) -> bool:
    return enqueue_task(refresh_candidate_queue_task, user_id)
