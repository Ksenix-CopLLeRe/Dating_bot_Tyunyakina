import asyncio
import logging
import os

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from dotenv import load_dotenv


load_dotenv()


BOT_TOKEN = os.getenv("BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000").rstrip("/")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not configured.")


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("dating-bot")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


async def register_user(telegram_id: str, username: str | None) -> dict:
    payload = {"telegram_id": telegram_id, "username": username}

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/users/register",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as response:
            response.raise_for_status()
            return await response.json()


async def fetch_backend_health() -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{BACKEND_URL}/health",
            timeout=aiohttp.ClientTimeout(total=10),
        ) as response:
            response.raise_for_status()
            return await response.json()


@dp.message(CommandStart())
async def start(message: Message):
    telegram_id = str(message.from_user.id)
    username = message.from_user.username

    try:
        payload = await register_user(telegram_id, username)
    except aiohttp.ClientError:
        logger.exception("Registration request failed for telegram_id=%s", telegram_id)
        await message.answer(
            "Не получилось связаться с backend-сервисом.\n"
            "Проверь, что API поднят и доступен."
        )
        return

    user = payload["user"]
    created = payload["created"]
    status_text = "регистрация завершена" if created else "ты уже был зарегистрирован"
    username_text = user["username"] or "без username"

    await message.answer(
        "Добро пожаловать в Твой Мэтч 🩷🤍\n\n"
        "✅ Твоя регистрация успешно завершена\n\n"
        "Теперь ты можешь создать свою анкету, находить интересных людей и получать "
        "персональные рекомендации для знакомств.\n\n"
        "✨️ Приятного общения и удачных мэтчей"
    )


@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "Команды бота:\n"
        "/start - зарегистрироваться или подтвердить регистрацию\n"
        "/help - показать список команд\n"
        "/ping - проверить связь с backend"
    )


@dp.message(Command("ping"))
async def ping_command(message: Message):
    try:
        payload = await fetch_backend_health()
    except aiohttp.ClientError:
        logger.exception("Healthcheck request failed")
        await message.answer("Backend сейчас недоступен.")
        return

    await message.answer(
        "Backend доступен.\n"
        f"Статус: {payload['status']}\n"
        f"База данных: {payload['database']}"
    )


async def main():
    logger.info("Starting bot polling")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
