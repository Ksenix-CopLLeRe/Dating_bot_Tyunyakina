import asyncio
import logging
import os

import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BotCommand, KeyboardButton, Message, ReplyKeyboardMarkup
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

BTN_CREATE_PROFILE = "Создать анкету"
BTN_UPDATE_PROFILE = "Обновить анкету"
BTN_MY_PROFILE = "Моя анкета"
BTN_DELETE_PROFILE = "Удалить анкету"
BTN_BROWSE = "Смотреть анкеты"
BTN_LIKE = "Лайк"
BTN_SKIP = "Пропустить"
BTN_MATCHES = "Мои мэтчи"
BTN_MY_LIKES = "Мои лайки"
BTN_RATING = "Мой рейтинг"
BTN_HELP = "Помощь"
BTN_CANCEL = "Отмена"
BTN_DIALOG = "Начать диалог"
BTN_DONE = "Готово"

GENDER_WOMAN = "Женщина"
GENDER_MAN = "Мужчина"
PREF_ANY = "Без фильтра"


class ProfileForm(StatesGroup):
    name = State()
    age = State()
    gender = State()
    city = State()
    interests = State()
    bio = State()
    photo = State()
    preferred_gender = State()
    preferred_age_min = State()
    preferred_age_max = State()
    preferred_city = State()


class DialogForm(StatesGroup):
    target_telegram_id = State()


class UpdateProfileForm(StatesGroup):
    field_selection = State()


PROFILE_STEPS = [
    ("name", "Как тебя зовут? Укажи имя или ник для анкеты."),
    ("age", "Укажи возраст числом, например `24`."),
    ("gender", "Выбери пол кнопкой ниже."),
    ("city", "Укажи город."),
    ("interests", "Напиши интересы через запятую."),
    ("bio", "Коротко расскажи о себе."),
    ("photo", "Прикрепи фотографию одним сообщением."),
    ("preferred_gender", "Кто тебе интересен? Выбери кнопкой ниже."),
    ("preferred_age_min", "Минимальный возраст кандидата. Если без фильтра, нажми `Без фильтра`."),
    ("preferred_age_max", "Максимальный возраст кандидата. Если без фильтра, нажми `Без фильтра`."),
    ("preferred_city", "Предпочитаемый город. Если без фильтра, нажми `Без фильтра`."),
]

PROFILE_PROMPTS = dict(PROFILE_STEPS)
UPDATE_FIELD_OPTIONS = [
    ("name", "Имя"),
    ("age", "Возраст"),
    ("gender", "Пол"),
    ("city", "Город"),
    ("interests", "Интересы"),
    ("bio", "О себе"),
    ("photo", "Фото"),
    ("preferred_gender", "Предпочитаемый пол"),
    ("preferred_age_min", "Мин. возраст"),
    ("preferred_age_max", "Макс. возраст"),
    ("preferred_city", "Предпочитаемый город"),
]
UPDATE_FIELD_BY_LABEL = {label: field for field, label in UPDATE_FIELD_OPTIONS}
UPDATE_LABEL_BY_FIELD = {field: label for field, label in UPDATE_FIELD_OPTIONS}


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_CREATE_PROFILE), KeyboardButton(text=BTN_UPDATE_PROFILE)],
            [KeyboardButton(text=BTN_MY_PROFILE), KeyboardButton(text=BTN_BROWSE)],
            [KeyboardButton(text=BTN_MATCHES), KeyboardButton(text=BTN_MY_LIKES)],
            [KeyboardButton(text=BTN_RATING), KeyboardButton(text=BTN_DIALOG)],
            [KeyboardButton(text=BTN_DELETE_PROFILE), KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
    )


def browse_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_LIKE), KeyboardButton(text=BTN_SKIP)],
            [KeyboardButton(text=BTN_MATCHES), KeyboardButton(text=BTN_MY_LIKES)],
            [KeyboardButton(text=BTN_RATING), KeyboardButton(text=BTN_HELP)],
            [KeyboardButton(text=BTN_MY_PROFILE)],
        ],
        resize_keyboard=True,
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_CANCEL)]],
        resize_keyboard=True,
    )


def gender_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=GENDER_WOMAN), KeyboardButton(text=GENDER_MAN)]],
        resize_keyboard=True,
    )


def preference_gender_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=GENDER_WOMAN), KeyboardButton(text=GENDER_MAN)],
            [KeyboardButton(text=PREF_ANY)],
        ],
        resize_keyboard=True,
    )


def any_filter_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=PREF_ANY)], [KeyboardButton(text=BTN_CANCEL)]],
        resize_keyboard=True,
    )


def update_profile_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=UPDATE_FIELD_OPTIONS[0][1]), KeyboardButton(text=UPDATE_FIELD_OPTIONS[1][1])],
        [KeyboardButton(text=UPDATE_FIELD_OPTIONS[2][1]), KeyboardButton(text=UPDATE_FIELD_OPTIONS[3][1])],
        [KeyboardButton(text=UPDATE_FIELD_OPTIONS[4][1]), KeyboardButton(text=UPDATE_FIELD_OPTIONS[5][1])],
        [KeyboardButton(text=UPDATE_FIELD_OPTIONS[6][1]), KeyboardButton(text=UPDATE_FIELD_OPTIONS[7][1])],
        [KeyboardButton(text=UPDATE_FIELD_OPTIONS[8][1]), KeyboardButton(text=UPDATE_FIELD_OPTIONS[9][1])],
        [KeyboardButton(text=UPDATE_FIELD_OPTIONS[10][1])],
        [KeyboardButton(text=BTN_DONE), KeyboardButton(text=BTN_CANCEL)],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


async def configure_bot_commands() -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Запустить бота"),
            BotCommand(command="help", description="Показать помощь"),
            BotCommand(command="cancel", description="Отменить текущее действие"),
        ]
    )


async def api_request(
    method: str,
    path: str,
    *,
    json_data: dict | None = None,
) -> tuple[int, dict]:
    async with aiohttp.ClientSession() as session:
        async with session.request(
            method,
            f"{BACKEND_URL}{path}",
            json=json_data,
            timeout=aiohttp.ClientTimeout(total=20),
        ) as response:
            payload = await response.json(content_type=None)
            return response.status, payload


def telegram_id_from_message(message: Message) -> str:
    return str(message.from_user.id)


def normalize_choice(raw_value: str) -> str:
    value = raw_value.strip()
    if value == GENDER_WOMAN:
        return "женщина"
    if value == GENDER_MAN:
        return "мужчина"
    return value.lower()


def nullable_value(raw_value: str) -> str | None:
    stripped = raw_value.strip()
    if stripped in {"-", PREF_ANY}:
        return None
    return normalize_choice(stripped)


def nullable_text(raw_value: str) -> str | None:
    stripped = raw_value.strip()
    if stripped in {"-", PREF_ANY}:
        return None
    return stripped


def build_profile_payload(data: dict) -> dict:
    return {
        "name": data["name"].strip(),
        "age": int(data["age"]),
        "gender": normalize_choice(data["gender"]),
        "city": data["city"].strip(),
        "interests": data["interests"].strip(),
        "bio": data["bio"].strip(),
        "photo_url": data["photo_file_id"],
        "preferred_gender": nullable_value(data["preferred_gender"]),
        "preferred_age_min": None
        if data["preferred_age_min"].strip() in {"-", PREF_ANY}
        else int(data["preferred_age_min"]),
        "preferred_age_max": None
        if data["preferred_age_max"].strip() in {"-", PREF_ANY}
        else int(data["preferred_age_max"]),
        "preferred_city": None
        if data["preferred_city"].strip() in {"-", PREF_ANY}
        else data["preferred_city"].strip(),
    }


def build_single_field_payload(field_name: str, data: dict, current_profile: dict | None = None) -> dict:
    if field_name == "name":
        return {"name": data["name"].strip()}
    if field_name == "age":
        return {"age": int(data["age"])}
    if field_name == "gender":
        return {"gender": normalize_choice(data["gender"])}
    if field_name == "city":
        return {"city": data["city"].strip()}
    if field_name == "interests":
        return {"interests": data["interests"].strip()}
    if field_name == "bio":
        return {"bio": data["bio"].strip()}
    if field_name == "photo":
        return {"photo_url": data["photo_file_id"]}
    if field_name == "preferred_gender":
        return {"preferred_gender": nullable_value(data["preferred_gender"])}
    if field_name == "preferred_city":
        return {"preferred_city": nullable_text(data["preferred_city"])}
    if field_name == "preferred_age_min":
        payload = {
            "preferred_age_min": None if data["preferred_age_min"].strip() in {"-", PREF_ANY} else int(data["preferred_age_min"]),
        }
        if current_profile and current_profile.get("preferred_age_max") is not None:
            payload["preferred_age_max"] = current_profile["preferred_age_max"]
        return payload
    if field_name == "preferred_age_max":
        payload = {
            "preferred_age_max": None if data["preferred_age_max"].strip() in {"-", PREF_ANY} else int(data["preferred_age_max"]),
        }
        if current_profile and current_profile.get("preferred_age_min") is not None:
            payload["preferred_age_min"] = current_profile["preferred_age_min"]
        return payload
    raise ValueError(f"Unsupported profile field: {field_name}")


def format_profile(profile: dict) -> str:
    return (
        "Твоя анкета:\n"
        f"Имя: {profile.get('name', 'не указано')}\n"
        f"Возраст: {profile.get('age', 'не указан')}\n"
        f"Пол: {profile.get('gender', 'не указан')}\n"
        f"Город: {profile.get('city', 'не указан')}\n"
        f"Интересы: {profile.get('interests', 'не указаны')}\n"
        f"О себе: {profile.get('bio', 'не указано')}\n"
        f"Предпочитаемый пол: {profile.get('preferred_gender') or 'без фильтра'}\n"
        f"Возраст кандидата: {profile.get('preferred_age_min') or '-'} - {profile.get('preferred_age_max') or '-'}\n"
        f"Предпочитаемый город: {profile.get('preferred_city') or 'без фильтра'}"
    )


def format_candidate(candidate: dict) -> str:
    profile = candidate["profile"]
    rating = candidate.get("rating")
    rating_text = (
        f"Рейтинг: {rating['final_score']:.1f} "
        f"(L1: {rating['level1_score']:.1f}, L2: {rating['level2_score']:.1f})"
        if rating
        else "Рейтинг: еще не рассчитан"
    )
    return (
        "Кандидат для знакомства:\n"
        f"Имя: {profile.get('name') or 'не указано'}\n"
        f"Username: {candidate.get('username') or 'без username'}\n"
        f"Возраст: {profile.get('age')}\n"
        f"Пол: {profile.get('gender')}\n"
        f"Город: {profile.get('city')}\n"
        f"Интересы: {profile.get('interests')}\n"
        f"О себе: {profile.get('bio')}\n"
        f"{rating_text}\n"
        f"Кэшировано кандидатов: {candidate.get('remaining_cached_candidates')}"
    )


def format_like_entry(like: dict) -> str:
    profile = like.get("profile") or {}
    status = "мэтч" if like.get("is_match") else "ожидание ответа"
    username = f"@{like['other_username']}" if like.get("other_username") else "без username"
    return (
        f"- {profile.get('name') or 'Без имени'} ({username}, "
        f"{profile.get('age') or 'возраст не указан'}, {profile.get('city') or 'город не указан'})"
        f" [{status}]"
    )


def rating_explanation_text(payload: dict) -> str:
    return (
        "Коротко: рейтинг складывается из двух частей.\n"
        f"Level 1 = заполненность анкеты ({payload['level1_score']:.1f}).\n"
        f"Level 2 = активность и реакции на тебя: лайки, мэтчи, диалоги ({payload['level2_score']:.1f}).\n"
        f"Итоговый score = среднее этих двух значений ({payload['final_score']:.1f})."
    )


async def prompt_for_profile_field(message: Message, state: FSMContext, field_name: str) -> None:
    reply_markup = cancel_keyboard()
    if field_name == "gender":
        reply_markup = gender_keyboard()
    elif field_name == "preferred_gender":
        reply_markup = preference_gender_keyboard()
    elif field_name in {"preferred_age_min", "preferred_age_max", "preferred_city"}:
        reply_markup = any_filter_keyboard()

    await state.set_state(getattr(ProfileForm, field_name))
    await message.answer(PROFILE_PROMPTS[field_name], reply_markup=reply_markup)


async def submit_single_field_update(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    field_name = data["selected_field"]
    telegram_id = telegram_id_from_message(message)
    status, current_profile = await api_request("GET", f"/profiles/{telegram_id}")
    if status >= 400:
        await state.clear()
        await message.answer(
            f"Не удалось получить текущую анкету: {current_profile.get('detail', current_profile)}",
            reply_markup=main_menu_keyboard(),
        )
        return

    payload = build_single_field_payload(field_name, data, current_profile)
    status, response = await api_request("PUT", f"/profiles/{telegram_id}", json_data=payload)
    if status >= 400:
        await message.answer(
            f"Не удалось обновить поле: {response.get('detail', response)}",
            reply_markup=update_profile_keyboard(),
        )
        await state.set_state(UpdateProfileForm.field_selection)
        return

    await state.set_data({"mode": "update_single"})
    await state.set_state(UpdateProfileForm.field_selection)
    await send_profile_photo(
        message,
        response.get("photo_url"),
        f"Поле `{UPDATE_LABEL_BY_FIELD[field_name]}` обновлено.\n\n{format_profile(response)}",
    )
    await message.answer("Выбери, что еще хочешь обновить.", reply_markup=update_profile_keyboard())


async def send_like_notification(notification: dict | None) -> None:
    if not notification:
        return

    recipient_telegram_id = notification.get("recipient_telegram_id")
    liker_profile = notification.get("liker_profile") or {}
    if not recipient_telegram_id:
        return

    username = f"@{notification['liker_username']}" if notification.get("liker_username") else "без username"
    caption = (
        "Твою анкету лайкнули.\n"
        f"Кто: {liker_profile.get('name') or 'Без имени'} ({username}"
    )
    caption += (
        f")\nВозраст: {liker_profile.get('age') or 'не указан'}\n"
        f"Город: {liker_profile.get('city') or 'не указан'}\n"
        f"Интересы: {liker_profile.get('interests') or 'не указаны'}"
    )

    if liker_profile.get("photo_url"):
        await bot.send_photo(chat_id=int(recipient_telegram_id), photo=liker_profile["photo_url"], caption=caption)
    else:
        await bot.send_message(chat_id=int(recipient_telegram_id), text=caption)


async def send_profile_photo(message: Message, photo_file_id: str | None, caption: str) -> None:
    if photo_file_id:
        await message.answer_photo(photo=photo_file_id, caption=caption, reply_markup=main_menu_keyboard())
    else:
        await message.answer(caption, reply_markup=main_menu_keyboard())


async def show_next_candidate(message: Message, candidate: dict | None) -> None:
    if not candidate:
        await message.answer("Подходящих анкет сейчас нет.", reply_markup=main_menu_keyboard())
        return

    profile = candidate["profile"]
    caption = f"{format_candidate(candidate)}\n\nИспользуй кнопки `Лайк` или `Пропустить`."
    if profile.get("photo_url"):
        await message.answer_photo(
            photo=profile["photo_url"],
            caption=caption,
            reply_markup=browse_keyboard(),
        )
    else:
        await message.answer(caption, reply_markup=browse_keyboard())


async def continue_profile_form(message: Message, state: FSMContext, next_index: int) -> None:
    if next_index >= len(PROFILE_STEPS):
        data = await state.get_data()
        mode = data["mode"]
        if mode == "update_single":
            await submit_single_field_update(message, state)
            return
        telegram_id = telegram_id_from_message(message)
        payload = build_profile_payload(data)

        method = "POST" if mode == "create" else "PUT"
        status, response = await api_request(method, f"/profiles/{telegram_id}", json_data=payload)

        if status >= 400:
            await message.answer(
                f"Не удалось сохранить анкету: {response.get('detail', response)}",
                reply_markup=main_menu_keyboard(),
            )
            return

        await state.clear()
        await send_profile_photo(
            message,
            response.get("photo_url"),
            f"Анкета сохранена.\n\n{format_profile(response)}",
        )
        return

    field_name, _prompt = PROFILE_STEPS[next_index]
    await state.update_data(step_index=next_index)
    await prompt_for_profile_field(message, state, field_name)


async def start_profile_form(message: Message, state: FSMContext, mode: str) -> None:
    await state.clear()
    await state.update_data(mode=mode, step_index=0)
    await message.answer(
        "Сейчас соберем анкету шаг за шагом.\n"
        "Если хочешь остановиться, нажми `Отмена`.",
        reply_markup=cancel_keyboard(),
    )
    await continue_profile_form(message, state, 0)


async def handle_profile_step(message: Message, state: FSMContext, current_field: str) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer("Нужно отправить текстовое значение.")
        return

    if current_field == "gender" and text not in {GENDER_WOMAN, GENDER_MAN}:
        await message.answer("Выбери пол кнопкой ниже.", reply_markup=gender_keyboard())
        return

    if current_field == "preferred_gender" and text not in {GENDER_WOMAN, GENDER_MAN, PREF_ANY}:
        await message.answer(
            "Выбери вариант кнопкой ниже.",
            reply_markup=preference_gender_keyboard(),
        )
        return

    if current_field in {"age", "preferred_age_min", "preferred_age_max"} and text not in {PREF_ANY, "-"}:
        if not text.isdigit():
            await message.answer("Здесь нужно число или кнопка `Без фильтра`.")
            return

    await state.update_data(**{current_field: text})
    data = await state.get_data()
    next_index = data["step_index"] + 1
    await continue_profile_form(message, state, next_index)


async def register_user_in_backend(message: Message) -> bool:
    telegram_id = telegram_id_from_message(message)
    username = message.from_user.username

    try:
        status, payload = await api_request(
            "POST",
            "/users/register",
            json_data={"telegram_id": telegram_id, "username": username},
        )
    except aiohttp.ClientError:
        logger.exception("Registration request failed for telegram_id=%s", telegram_id)
        await message.answer(
            "Не получилось связаться с backend-сервисом.\n"
            "Проверь, что API поднят и доступен."
        )
        return False

    if status >= 400:
        await message.answer(f"Ошибка регистрации: {payload}", reply_markup=main_menu_keyboard())
        return False

    return True


@dp.message(CommandStart())
async def start(message: Message):
    if not await register_user_in_backend(message):
        return

    await message.answer(
        "Добро пожаловать в Твой Мэтч 🩷🤍\n\n"
        "✅ Твоя регистрация успешно завершена\n\n"
        "Теперь ты можешь создать свою анкету, находить интересных людей и получать "
        "персональные рекомендации для знакомств.\n\n"
        "✨️ Приятного общения и удачных мэтчей",
        reply_markup=main_menu_keyboard(),
    )


@dp.message(Command("help"))
@dp.message(F.text == BTN_HELP)
async def help_command(message: Message):
    await message.answer(
        "Доступные действия:\n"
        "• Создать анкету\n"
        "• Обновить анкету по выбранным полям\n"
        "• Посмотреть свою анкету\n"
        "• Смотреть анкеты\n"
        "• Ставить лайки и пропуски\n"
        "• Смотреть свои последние лайки\n"
        "• Смотреть мэтчи и рейтинг\n"
        "• Отметить начало диалога кнопкой `Начать диалог`\n\n"
        "Основные действия доступны кнопками под полем ввода.",
        reply_markup=main_menu_keyboard(),
    )


@dp.message(Command("cancel"))
@dp.message(F.text == BTN_CANCEL)
async def cancel_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Текущее действие отменено.", reply_markup=main_menu_keyboard())


@dp.message(F.text == BTN_CREATE_PROFILE)
@dp.message(Command("create_profile"))
async def create_profile_command(message: Message, state: FSMContext):
    await start_profile_form(message, state, "create")


@dp.message(F.text == BTN_UPDATE_PROFILE)
@dp.message(Command("update_profile"))
async def update_profile_command(message: Message, state: FSMContext):
    await state.clear()
    await state.update_data(mode="update_single")
    await state.set_state(UpdateProfileForm.field_selection)
    await message.answer(
        "Выбери кнопкой, что именно хочешь обновить в анкете.",
        reply_markup=update_profile_keyboard(),
    )


@dp.message(UpdateProfileForm.field_selection)
async def update_profile_field_selection(message: Message, state: FSMContext):
    choice = (message.text or "").strip()
    if choice == BTN_DONE:
        await state.clear()
        await message.answer("Обновление анкеты завершено.", reply_markup=main_menu_keyboard())
        return

    field_name = UPDATE_FIELD_BY_LABEL.get(choice)
    if not field_name:
        await message.answer(
            "Выбери поле кнопкой ниже или нажми `Готово`.",
            reply_markup=update_profile_keyboard(),
        )
        return

    await state.update_data(
        mode="update_single",
        selected_field=field_name,
        step_index=len(PROFILE_STEPS) - 1,
    )
    await prompt_for_profile_field(message, state, field_name)


@dp.message(F.text == BTN_MY_PROFILE)
@dp.message(Command("my_profile"))
async def my_profile_command(message: Message):
    status, payload = await api_request("GET", f"/profiles/{telegram_id_from_message(message)}")
    if status >= 400:
        await message.answer(
            f"Не удалось получить анкету: {payload.get('detail', payload)}",
            reply_markup=main_menu_keyboard(),
        )
        return
    await send_profile_photo(message, payload.get("photo_url"), format_profile(payload))


@dp.message(F.text == BTN_DELETE_PROFILE)
@dp.message(Command("delete_profile"))
async def delete_profile_command(message: Message):
    status, payload = await api_request("DELETE", f"/profiles/{telegram_id_from_message(message)}")
    if status >= 400:
        await message.answer(
            f"Не удалось удалить анкету: {payload.get('detail', payload)}",
            reply_markup=main_menu_keyboard(),
        )
        return
    await message.answer(payload["message"], reply_markup=main_menu_keyboard())


@dp.message(F.text == BTN_BROWSE)
@dp.message(Command("browse"))
async def browse_command(message: Message):
    status, payload = await api_request("GET", f"/profiles/{telegram_id_from_message(message)}/candidate")
    if status >= 400:
        await message.answer(
            f"Не удалось получить кандидата: {payload.get('detail', payload)}",
            reply_markup=main_menu_keyboard(),
        )
        return
    await show_next_candidate(message, payload)


@dp.message(F.text == BTN_LIKE)
@dp.message(Command("like"))
async def like_command(message: Message):
    status, payload = await api_request("POST", f"/interactions/{telegram_id_from_message(message)}/like")
    if status >= 400:
        await message.answer(
            f"Не удалось поставить лайк: {payload.get('detail', payload)}",
            reply_markup=main_menu_keyboard(),
        )
        return

    await message.answer(payload["message"], reply_markup=browse_keyboard())
    try:
        await send_like_notification(payload.get("like_notification"))
    except Exception:
        logger.exception("Failed to send like notification")
    await show_next_candidate(message, payload.get("next_candidate"))


@dp.message(F.text == BTN_SKIP)
@dp.message(Command("skip"))
async def skip_command(message: Message):
    status, payload = await api_request("POST", f"/interactions/{telegram_id_from_message(message)}/skip")
    if status >= 400:
        await message.answer(
            f"Не удалось пропустить анкету: {payload.get('detail', payload)}",
            reply_markup=main_menu_keyboard(),
        )
        return

    await message.answer(payload["message"], reply_markup=browse_keyboard())
    await show_next_candidate(message, payload.get("next_candidate"))


@dp.message(F.text == BTN_MATCHES)
@dp.message(Command("matches"))
async def matches_command(message: Message):
    status, payload = await api_request("GET", f"/matches/{telegram_id_from_message(message)}")
    if status >= 400:
        await message.answer(
            f"Не удалось получить мэтчи: {payload.get('detail', payload)}",
            reply_markup=main_menu_keyboard(),
        )
        return

    matches = payload.get("matches", [])
    if not matches:
        await message.answer("Мэтчей пока нет.", reply_markup=main_menu_keyboard())
        return

    lines = ["Твои мэтчи:"]
    for match in matches:
        profile = match.get("profile") or {}
        lines.append(
            f"- {match.get('other_username') or 'без username'} "
            f"(telegram user id: {match['other_user_id']}, "
            f"город: {profile.get('city') or 'не указан'}, "
            f"интересы: {profile.get('interests') or 'не указаны'})"
        )

    await message.answer("\n".join(lines), reply_markup=main_menu_keyboard())


@dp.message(F.text == BTN_MY_LIKES)
@dp.message(Command("my_likes"))
async def my_likes_command(message: Message):
    status, payload = await api_request("GET", f"/likes/{telegram_id_from_message(message)}")
    if status >= 400:
        await message.answer(
            f"Не удалось получить лайки: {payload.get('detail', payload)}",
            reply_markup=main_menu_keyboard(),
        )
        return

    likes = payload.get("likes", [])
    if not likes:
        await message.answer("У тебя пока нет сохраненных лайков.", reply_markup=main_menu_keyboard())
        return

    lines = ["Твои последние лайки:"]
    lines.extend(format_like_entry(like) for like in likes)
    await message.answer("\n".join(lines), reply_markup=main_menu_keyboard())


@dp.message(F.text == BTN_RATING)
@dp.message(Command("rating"))
async def rating_command(message: Message):
    status, payload = await api_request("GET", f"/ratings/{telegram_id_from_message(message)}")
    if status >= 400:
        await message.answer(
            f"Не удалось получить рейтинг: {payload.get('detail', payload)}",
            reply_markup=main_menu_keyboard(),
        )
        return

    await message.answer(
        "Твой рейтинг:\n"
        f"Level 1: {payload['level1_score']:.1f}\n"
        f"Level 2: {payload['level2_score']:.1f}\n"
        f"Итоговый score: {payload['final_score']:.1f}\n\n"
        f"{rating_explanation_text(payload)}",
        reply_markup=main_menu_keyboard(),
    )


@dp.message(F.text == BTN_DIALOG)
async def start_dialog_button(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(DialogForm.target_telegram_id)
    await message.answer(
        "Отправь `telegram_id` пользователя, с которым хочешь отметить начало диалога.",
        reply_markup=cancel_keyboard(),
    )


@dp.message(Command("open_dialog"))
async def open_dialog_command(message: Message, command: CommandObject):
    if not command.args:
        await message.answer(
            "Использование: /open_dialog <telegram_id>",
            reply_markup=main_menu_keyboard(),
        )
        return

    other_telegram_id = command.args.strip()
    status, payload = await api_request(
        "POST",
        f"/matches/{telegram_id_from_message(message)}/dialogs/{other_telegram_id}",
    )
    if status >= 400:
        await message.answer(
            f"Не удалось сохранить начало диалога: {payload.get('detail', payload)}",
            reply_markup=main_menu_keyboard(),
        )
        return

    await message.answer(payload["message"], reply_markup=main_menu_keyboard())


@dp.message(DialogForm.target_telegram_id)
async def open_dialog_from_button(message: Message, state: FSMContext):
    other_telegram_id = (message.text or "").strip()
    if not other_telegram_id.isdigit():
        await message.answer("Нужен числовой `telegram_id`.", reply_markup=cancel_keyboard())
        return

    status, payload = await api_request(
        "POST",
        f"/matches/{telegram_id_from_message(message)}/dialogs/{other_telegram_id}",
    )
    if status >= 400:
        await message.answer(
            f"Не удалось сохранить начало диалога: {payload.get('detail', payload)}",
            reply_markup=main_menu_keyboard(),
        )
        await state.clear()
        return

    await state.clear()
    await message.answer(payload["message"], reply_markup=main_menu_keyboard())


@dp.message(ProfileForm.name)
async def profile_name(message: Message, state: FSMContext):
    await handle_profile_step(message, state, "name")


@dp.message(ProfileForm.age)
async def profile_age(message: Message, state: FSMContext):
    await handle_profile_step(message, state, "age")


@dp.message(ProfileForm.gender)
async def profile_gender(message: Message, state: FSMContext):
    await handle_profile_step(message, state, "gender")


@dp.message(ProfileForm.city)
async def profile_city(message: Message, state: FSMContext):
    await handle_profile_step(message, state, "city")


@dp.message(ProfileForm.interests)
async def profile_interests(message: Message, state: FSMContext):
    await handle_profile_step(message, state, "interests")


@dp.message(ProfileForm.bio)
async def profile_bio(message: Message, state: FSMContext):
    await handle_profile_step(message, state, "bio")


@dp.message(ProfileForm.photo, F.photo)
async def profile_photo(message: Message, state: FSMContext):
    photo_file_id = message.photo[-1].file_id
    await state.update_data(photo_file_id=photo_file_id)
    data = await state.get_data()
    next_index = data["step_index"] + 1
    await continue_profile_form(message, state, next_index)


@dp.message(ProfileForm.photo)
async def profile_photo_invalid(message: Message):
    await message.answer("Нужно отправить именно фотографию одним сообщением.", reply_markup=cancel_keyboard())


@dp.message(ProfileForm.preferred_gender)
async def profile_preferred_gender(message: Message, state: FSMContext):
    await handle_profile_step(message, state, "preferred_gender")


@dp.message(ProfileForm.preferred_age_min)
async def profile_preferred_age_min(message: Message, state: FSMContext):
    await handle_profile_step(message, state, "preferred_age_min")


@dp.message(ProfileForm.preferred_age_max)
async def profile_preferred_age_max(message: Message, state: FSMContext):
    await handle_profile_step(message, state, "preferred_age_max")


@dp.message(ProfileForm.preferred_city)
async def profile_preferred_city(message: Message, state: FSMContext):
    await handle_profile_step(message, state, "preferred_city")


@dp.message(F.text)
async def fallback_handler(message: Message):
    await message.answer("Не понял действие. Используй кнопки под полем ввода.", reply_markup=main_menu_keyboard())


async def main():
    logger.info("Starting bot polling")
    await configure_bot_commands()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
