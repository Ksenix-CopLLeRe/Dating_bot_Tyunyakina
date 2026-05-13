from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiogram import Bot
from aiogram.types import BufferedInputFile
from kombu import Connection
from kombu.mixins import ConsumerMixin

from . import crud, storage
from .config import BOT_TOKEN, RABBITMQ_URL
from .database import SessionLocal
from .events import NOTIFICATION_QUEUE
from .logging_config import configure_logging


configure_logging()
logger = logging.getLogger(__name__)


class NotificationConsumer(ConsumerMixin):
    def __init__(self, connection: Connection):
        self.connection = connection

    def get_consumers(self, Consumer, channel):
        return [
            Consumer(
                queues=[NOTIFICATION_QUEUE],
                callbacks=[self.process_message],
                accept=["json"],
                prefetch_count=1,
            )
        ]

    def process_message(self, body: dict[str, Any], message) -> None:
        try:
            asyncio.run(handle_event(body))
        except Exception:
            logger.exception("notification.event_failed", extra={"event": body})
            message.reject(requeue=False)
            return

        message.ack()


async def handle_event(event: dict[str, Any]) -> None:
    event_type = event.get("event_type")
    actor_user_id = event.get("actor_user_id")
    target_user_id = event.get("target_user_id")
    payload = event.get("payload") or {}

    if event_type == "profile_liked":
        await handle_profile_liked(actor_user_id, target_user_id, payload)
    elif event_type == "dialog_started":
        await handle_dialog_started(actor_user_id, target_user_id, payload)
    elif event_type == "user_registered":
        await handle_user_registered(actor_user_id, target_user_id, payload)
    else:
        logger.info("notification.event_ignored", extra={"event_type": event_type})


async def handle_profile_liked(
    liker_user_id: int | None,
    recipient_user_id: int | None,
    payload: dict[str, Any],
) -> None:
    if not liker_user_id or not recipient_user_id:
        return

    db = SessionLocal()
    try:
        liker = crud.get_user_by_id(db, liker_user_id)
        recipient = crud.get_user_by_id(db, recipient_user_id)
        liker_profile = crud.get_profile_by_user_id(db, liker_user_id)
        if not recipient or not liker_profile:
            return

        username = f"@{liker.username}" if liker and liker.username else "без username"
        caption = (
            "Твою анкету лайкнули.\n"
            f"Кто: {liker_profile.name or 'Без имени'} ({username})\n"
            f"Возраст: {liker_profile.age or 'не указан'}\n"
            f"Город: {liker_profile.city or 'не указан'}\n"
            f"Интересы: {liker_profile.interests or 'не указаны'}"
        )
        await send_profile_notification(recipient.telegram_id, caption, liker_profile.photo_url)

        if payload.get("is_match"):
            await notify_match(db, liker_user_id, recipient_user_id)
    finally:
        db.close()


async def notify_match(db, user_a_id: int, user_b_id: int) -> None:
    user_a = crud.get_user_by_id(db, user_a_id)
    user_b = crud.get_user_by_id(db, user_b_id)
    profile_a = crud.get_profile_by_user_id(db, user_a_id)
    profile_b = crud.get_profile_by_user_id(db, user_b_id)
    if not user_a or not user_b:
        return

    if profile_b:
        await send_text(
            user_a.telegram_id,
            "Взаимный лайк! У вас мэтч.\n"
            f"Пользователь: {profile_b.name or user_b.username or 'Без имени'}\n"
            f"Telegram ID для диалога: {user_b.telegram_id}\n"
            f"Команда: /open_dialog {user_b.telegram_id}",
        )
    if profile_a:
        await send_text(
            user_b.telegram_id,
            "Взаимный лайк! У вас мэтч.\n"
            f"Пользователь: {profile_a.name or user_a.username or 'Без имени'}\n"
            f"Telegram ID для диалога: {user_a.telegram_id}\n"
            f"Команда: /open_dialog {user_a.telegram_id}",
        )


async def handle_dialog_started(
    actor_user_id: int | None,
    target_user_id: int | None,
    payload: dict[str, Any],
) -> None:
    if not actor_user_id or not target_user_id:
        return

    db = SessionLocal()
    try:
        actor = crud.get_user_by_id(db, actor_user_id)
        target = crud.get_user_by_id(db, target_user_id)
        actor_profile = crud.get_profile_by_user_id(db, actor_user_id)
        if not actor or not target:
            return

        await send_text(
            target.telegram_id,
            "После мэтча отметили начало диалога с тобой.\n"
            f"Кто: {actor_profile.name if actor_profile and actor_profile.name else actor.username or actor.telegram_id}",
        )
    finally:
        db.close()


async def handle_user_registered(
    new_user_id: int | None,
    referrer_user_id: int | None,
    payload: dict[str, Any],
) -> None:
    if not new_user_id or not referrer_user_id:
        return

    db = SessionLocal()
    try:
        new_user = crud.get_user_by_id(db, new_user_id)
        referrer = crud.get_user_by_id(db, referrer_user_id)
        if not new_user or not referrer:
            return
        await send_text(
            referrer.telegram_id,
            "По твоей реферальной ссылке зарегистрировался новый пользователь.\n"
            f"Username: @{new_user.username}" if new_user.username else "По твоей реферальной ссылке зарегистрировался новый пользователь.",
        )
    finally:
        db.close()


async def send_profile_notification(
    telegram_id: str,
    caption: str,
    photo_reference: str | None,
) -> None:
    if photo_reference:
        try:
            photo = build_telegram_photo(photo_reference)
            await send_photo(telegram_id, photo, caption)
            return
        except Exception:
            logger.exception("notification.photo_failed", extra={"telegram_id": telegram_id})

    await send_text(telegram_id, caption)


def build_telegram_photo(photo_reference: str) -> str | BufferedInputFile:
    if photo_reference.startswith("profiles/"):
        content, _content_type = storage.download_photo(photo_reference)
        return BufferedInputFile(content, filename="profile-photo.jpg")
    return photo_reference


async def send_text(telegram_id: str, text: str) -> None:
    if not BOT_TOKEN:
        logger.warning("notification.bot_token_missing")
        return

    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_message(chat_id=int(telegram_id), text=text)
        logger.info("notification.sent_text", extra={"telegram_id": telegram_id})
    finally:
        await bot.session.close()


async def send_photo(telegram_id: str, photo: str | BufferedInputFile, caption: str) -> None:
    if not BOT_TOKEN:
        logger.warning("notification.bot_token_missing")
        return

    bot = Bot(token=BOT_TOKEN)
    try:
        await bot.send_photo(chat_id=int(telegram_id), photo=photo, caption=caption)
        logger.info("notification.sent_photo", extra={"telegram_id": telegram_id})
    finally:
        await bot.session.close()


def main() -> None:
    if not BOT_TOKEN:
        logger.warning("notification.bot_token_missing_on_start")

    logger.info("notification.consumer_starting", extra={"queue": NOTIFICATION_QUEUE.name})
    with Connection(RABBITMQ_URL) as connection:
        NotificationConsumer(connection).run()


if __name__ == "__main__":
    main()
