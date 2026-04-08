import os
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message
import asyncio
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
BACKEND_URL = os.getenv("BACKEND_URL")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def start(message: Message):

    telegram_id = str(message.from_user.id)
    username = message.from_user.username

    response = requests.post(
        f"{BACKEND_URL}/users/register",
        json={
            "telegram_id": telegram_id,
            "username": username
        }
    )

    if response.status_code == 200:
        await message.answer(
            "Добро пожаловать в Dating Bot.\n"
            "Пользователь зарегистрирован."
        )
    else:
        await message.answer("Ошибка регистрации")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())