from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from kombu import Connection, Exchange, Producer, Queue
from kombu.exceptions import KombuError, OperationalError

from .config import RABBITMQ_URL


logger = logging.getLogger(__name__)

EVENT_EXCHANGE = Exchange("dating.events", type="topic", durable=True)
NOTIFICATION_QUEUE = Queue(
    "dating.notifications",
    exchange=EVENT_EXCHANGE,
    routing_key="dating.#",
    durable=True,
)


def publish_interaction_event(
    event_type: str,
    actor_user_id: int,
    target_user_id: int | None = None,
    payload: dict[str, Any] | None = None,
) -> bool:
    message = {
        "event_type": event_type,
        "actor_user_id": actor_user_id,
        "target_user_id": target_user_id,
        "payload": payload or {},
        "occurred_at": datetime.utcnow().isoformat(),
    }

    try:
        with Connection(RABBITMQ_URL, connect_timeout=2) as connection:
            producer = Producer(connection)
            producer.publish(
                message,
                exchange=EVENT_EXCHANGE,
                routing_key=f"dating.{event_type}",
                serializer="json",
                retry=False,
                declare=[EVENT_EXCHANGE],
            )
    except (KombuError, OperationalError, OSError) as exc:
        logger.warning(
            "mq.publish_failed",
            extra={"event_type": event_type, "actor_user_id": actor_user_id, "error": str(exc)},
        )
        return False

    logger.info(
        "mq.event_published",
        extra={"event_type": event_type, "actor_user_id": actor_user_id, "target_user_id": target_user_id},
    )
    return True


def check_mq_connection() -> bool:
    try:
        with Connection(RABBITMQ_URL, connect_timeout=2) as connection:
            connection.connect()
    except (KombuError, OperationalError, OSError):
        return False
    return True
