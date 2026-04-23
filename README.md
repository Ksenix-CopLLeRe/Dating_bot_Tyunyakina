# Dating Bot

Проект реализует первые два этапа практики по dating-боту:

1. планирование и проектирование системы
2. базовую функциональность Telegram-бота с регистрацией пользователя

Третий этап пока не реализован полностью: `CRUD` анкет, ранжирование, Redis-кэш, лайки и мэтчи остаются следующим шагом.

## Что реализовано

### Этап 1. Планирование и проектирование

- описана архитектура системы
- зафиксирована схема данных
- подготовлена инфраструктура запуска через Docker Compose
- в коде описаны основные сущности домена: `User`, `Profile`, `Like`, `Match`, `Rating`

### Этап 2. Базовая функциональность

- Telegram-бот на `aiogram`
- backend на `FastAPI`
- регистрация пользователя по команде `/start`
- повторный `/start` не создает дубликаты
- команда `/ping` проверяет доступность backend и базы

## Архитектура первых двух этапов

Сейчас проект состоит из трех реально используемых компонентов:

1. `bot`
   Telegram-бот, который принимает команды пользователя и вызывает backend API.
2. `backend`
   HTTP API с базовой бизнес-логикой и регистрацией пользователей.
3. `db`
   PostgreSQL, где хранятся пользователи и подготовленные таблицы следующих этапов.

Поток регистрации:

`Telegram User -> Bot -> Backend API -> PostgreSQL`

## Схема данных

В базе данных подготовлены следующие таблицы:

### `users`

- `id`
- `telegram_id`
- `username`
- `created_at`

### `profiles`

- `id`
- `user_id`
- `age`
- `gender`
- `city`
- `interests`
- `bio`
- `photo_url`
- `preferred_gender`
- `preferred_age_min`
- `preferred_age_max`
- `preferred_city`
- `created_at`
- `updated_at`

### `likes`

- `id`
- `from_user_id`
- `to_user_id`
- `created_at`

### `matches`

- `id`
- `user1_id`
- `user2_id`
- `created_at`

### `ratings`

- `user_id`
- `level1_score`
- `level2_score`
- `final_score`
- `updated_at`

## API

### `GET /`

Проверка, что backend запущен.

### `GET /health`

Проверка доступности backend и соединения с базой данных.

### `POST /users/register`

Регистрирует пользователя по `telegram_id`. Если пользователь уже есть, возвращает существующую запись.

Пример тела запроса:

```json
{
  "telegram_id": "123456789",
  "username": "demo_user"
}
```

### `GET /users/by-telegram/{telegram_id}`

Возвращает пользователя по Telegram ID.

## Команды бота

- `/start` - регистрация пользователя
- `/help` - список доступных команд
- `/ping` - проверка связи с backend

## Быстрый старт

1. Создать `.env` на основе `.env.example`
2. Указать реальный `BOT_TOKEN`
3. Запустить проект:

```bash
docker compose up --build
```

После запуска:

- backend будет доступен на `http://localhost:8000`
- PostgreSQL будет доступен на `localhost:5432`

## Структура проекта

```text
backend/
bot/
docker/
docs/
docker-compose.yml
requirements.txt
```

## Что дальше

Для полного закрытия третьего этапа нужно добавить:

- `CRUD` анкет
- выдачу анкет на просмотр
- лайки, пропуски, мэтчи
- ранжирование
- Redis-кэш анкет
