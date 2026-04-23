# Dating Bot

Проект закрывает первые три этапа практики по dating-боту:

1. планирование и проектирование
2. базовая функциональность Telegram-бота
3. система анкет и ранжирования

## Что реализовано

- `FastAPI` backend с `PostgreSQL`
- `Redis` для кеширования очереди кандидатов
- Telegram-бот на `aiogram`
- регистрация пользователя через `/start`
- полный `CRUD` анкет
- просмотр кандидатов, лайки, пропуски, мэтчи
- трехуровневый рейтинг с сохранением в таблице `ratings`
- кеширование следующих 10 кандидатов в `Redis`
- фиксация начала диалога после мэтча

## Схема данных

В проекте используются таблицы:

- `users`
- `profiles`
- `likes`
- `skips`
- `matches`
- `dialog_initiations`
- `ratings`

## Как работает третий этап

### Анкеты

Пользователь создает или редактирует анкету с полями:

- возраст
- пол
- город
- интересы
- `bio`
- `photo_url`
- предпочтения по полу, возрасту и городу

### Ранжирование

Рейтинг хранится в таблице `ratings` и пересчитывается при изменении анкеты и взаимодействиях.

- `Level 1`: полнота анкеты, фото, заполненные предпочтения
- `Level 2`: лайки, соотношение лайков и пропусков, мэтчи, начало диалогов, недавняя активность
- `Final score`: `0.5 * level1 + 0.5 * level2`

### Redis-кеш

Для каждого пользователя backend хранит в `Redis` очередь кандидатов.

- при первом запросе кандидата backend подбирает и ранжирует анкеты
- в кеш попадает до 10 следующих кандидатов
- после лайка или пропуска текущий кандидат удаляется из очереди
- когда кеш почти закончился, backend автоматически подгружает новую пачку

## API

Основные endpoint'ы:

- `POST /users/register`
- `POST /profiles/{telegram_id}`
- `GET /profiles/{telegram_id}`
- `PUT /profiles/{telegram_id}`
- `DELETE /profiles/{telegram_id}`
- `GET /profiles/{telegram_id}/candidate`
- `GET /profiles/{telegram_id}/queue-state`
- `POST /interactions/{telegram_id}/like`
- `POST /interactions/{telegram_id}/skip`
- `GET /matches/{telegram_id}`
- `POST /matches/{telegram_id}/dialogs/{other_telegram_id}`
- `GET /ratings/{telegram_id}`
- `GET /health`

## Команды бота

- `/start`
- `/help`
- `/ping`
- `/create_profile`
- `/update_profile`
- `/my_profile`
- `/delete_profile`
- `/browse`
- `/like`
- `/skip`
- `/matches`
- `/rating`
- `/open_dialog <telegram_id>`
- `/cancel`

## Быстрый старт

1. Создай `.env` на основе `.env.example`
2. Укажи реальный `BOT_TOKEN`
3. Запусти проект:

```bash
docker compose up --build
```

После запуска будут подняты:

- `db` на `localhost:5432`
- `redis` на `localhost:6379`
- `backend` на `http://localhost:8000`
- `bot`

## Важно

Если база уже была поднята на старой версии схемы, удобнее пересоздать контейнеры и volume базы перед первым запуском обновленного третьего этапа.
