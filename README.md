# Dating Bot

Telegram-бот для знакомств с backend на FastAPI. Пользователь регистрируется через Telegram, создает анкету, смотрит анкеты других пользователей, ставит лайки или пропускает кандидатов, получает мэтчи, видит свой рейтинг и может приглашать друзей по реферальной ссылке.

Проект реализован как небольшая backend-система, а не только как бот: есть база данных, кэширование кандидатов, фоновые задачи, брокер сообщений, метрики, тесты и локальный запуск через Docker Compose.

## Возможности

- Регистрация пользователя по Telegram ID при `/start`.
- Создание анкеты с возможностью пропускать поля.
- Просмотр и обновление своей анкеты.
- Удаление анкеты.
- Подбор кандидатов с учетом рейтинга и совместимости.
- Кэширование очереди кандидатов в Redis.
- Лайки и пропуски анкет.
- Автоматическое создание мэтча при взаимном лайке.
- Просмотр последних лайков.
- Просмотр мэтчей.
- Отметка начала диалога после мэтча.
- Рейтинг пользователя:
  - Level 1: заполненность анкеты;
  - Level 2: реакции и активность;
  - referral score: приглашенные пользователи.
- Реферальные ссылки через Telegram.
- RabbitMQ-события для регистраций, лайков, пропусков и диалогов.
- Celery-задачи для фонового пересчета рейтингов и прогрева очередей.
- Хранение фотографий анкет в MinIO/S3.
- Prometheus-метрики на `/metrics`.
- Healthcheck на `/health`.
- Автотесты через pytest.
- CI через GitHub Actions.
- JMeter-план для нагрузочного тестирования.

## Технологии

- Python 3.11+
- aiogram 3
- FastAPI
- SQLAlchemy
- PostgreSQL
- Redis
- RabbitMQ
- Celery
- MinIO / S3
- Prometheus
- Grafana
- Prometheus client
- pytest
- Docker Compose

## Структура проекта

```text
backend/
  main.py             FastAPI-приложение и API endpoints
  models.py           SQLAlchemy-модели таблиц
  schemas.py          Pydantic-схемы запросов и ответов
  crud.py             Работа с БД
  ranking.py          Алгоритм рейтинга
  cache.py            Redis-кэш очередей кандидатов
  tasks.py            Celery-задачи
  background.py       Безопасная отправка задач в Celery
  events.py           Публикация событий в RabbitMQ
  storage.py          Загрузка и чтение фотографий из MinIO/S3
  metrics.py          Продуктовые метрики для Prometheus/Grafana
  notification_service.py RabbitMQ consumer для Telegram-уведомлений
  database.py         Подключение к БД
  config.py           Переменные окружения
  logging_config.py   Настройка логирования

bot/
  bot.py              Telegram-бот и пользовательские сценарии

docker/
  Dockerfile.backend
  Dockerfile.bot

docs/
  performance.md
  stage4-load-test.jmx
  er-diagram.png

tests/
  test_stage4.py

.github/workflows/
  ci.yml
```

## Архитектура

```text
Telegram user
    |
    v
bot/bot.py
    |
    v
FastAPI backend
    |
    +--> PostgreSQL: пользователи, анкеты, лайки, мэтчи, рейтинги
    |
    +--> Redis: кэш предварительно отранжированных кандидатов
    |
    +--> RabbitMQ: события взаимодействий
    |
    +--> MinIO/S3: фотографии анкет
    |
    +--> Celery worker: фоновые задачи
    |
    +--> Prometheus -> Grafana: метрики, рейтинги, dashboard
```

Backend отвечает за бизнес-логику, Telegram-бот отвечает за интерфейс пользователя. Redis ускоряет выдачу кандидатов, RabbitMQ делает систему событийной, MinIO хранит фотографии анкет, Celery выносит периодические и фоновые операции из основного потока API, а Prometheus и Grafana показывают состояние продукта.

## Переменные окружения

Создайте `.env` из примера:

```bash
cp .env.example .env
```

Для PowerShell:

```powershell
copy .env.example .env
```

Основные переменные:

```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/dating_bot
REDIS_URL=redis://redis:6379/0
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672//
CELERY_BROKER_URL=amqp://guest:guest@rabbitmq:5672//
CELERY_RESULT_BACKEND=redis://redis:6379/0
S3_ENDPOINT_URL=http://minio:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
S3_BUCKET_NAME=dating-bot-photos
S3_REGION_NAME=us-east-1
BACKEND_URL=http://backend:8000
BOT_TOKEN=replace_with_real_telegram_bot_token
```

Перед запуском обязательно укажите настоящий `BOT_TOKEN`.

## Локальный запуск через Docker

```bash
docker compose up --build
```

После запуска доступны:

- FastAPI backend: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Healthcheck: `http://localhost:8000/health`
- Метрики: `http://localhost:8000/metrics`
- RabbitMQ UI: `http://localhost:15672`
- MinIO Console: `http://localhost:9001`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`

Логин и пароль RabbitMQ:

```text
guest / guest
```

Логин и пароль MinIO:

```text
minioadmin / minioadmin
```

Логин и пароль Grafana:

```text
admin / admin
```

## Сервисы Docker Compose

- `db` - PostgreSQL.
- `redis` - Redis.
- `rabbitmq` - RabbitMQ с management UI.
- `minio` - S3-совместимое хранилище фотографий.
- `backend` - FastAPI API.
- `celery_worker` - Celery worker для фоновых задач.
- `celery_beat` - Celery beat для регулярных задач.
- `notification_service` - отдельный RabbitMQ consumer, который отправляет Telegram-уведомления.
- `prometheus` - сборщик метрик с backend `/metrics`.
- `grafana` - UI с готовым dashboard по рейтингу и активности.
- `bot` - Telegram-бот.

## Основные сценарии в Telegram

1. Пользователь пишет `/start`.
2. Бот регистрирует пользователя в backend.
3. Пользователь нажимает `Создать анкету`.
4. Пользователь заполняет поля анкеты или нажимает `Пропустить поле`.
5. Пользователь нажимает `Смотреть анкеты`.
6. Бот показывает кандидата.
7. Пользователь нажимает `Лайк` или `Пропустить`.
8. При взаимном лайке создается мэтч.
9. Пользователь может открыть `Мои мэтчи`.
10. Пользователь может отметить начало диалога командой `/open_dialog <telegram_id>`.
11. Пользователь может посмотреть `Мой рейтинг`.
12. Пользователь может получить реферальную ссылку через `Пригласить друга`.

## API

Полная интерактивная документация доступна после запуска:

```text
http://localhost:8000/docs
```

Основные endpoints:

### System

- `GET /` - информация о сервисе.
- `GET /health` - проверка БД, Redis, RabbitMQ и Celery heartbeat.
- `GET /metrics` - Prometheus-метрики.

### Users

- `POST /users/register` - регистрация пользователя.
- `GET /users/by-telegram/{telegram_id}` - получение пользователя по Telegram ID.

### Profiles

- `POST /profiles/{telegram_id}` - создание анкеты.
- `GET /profiles/{telegram_id}` - получение своей анкеты.
- `PUT /profiles/{telegram_id}` - обновление анкеты.
- `DELETE /profiles/{telegram_id}` - удаление анкеты.
- `GET /profiles/{telegram_id}/candidate` - получить следующего кандидата.
- `GET /profiles/{telegram_id}/queue-state` - состояние Redis-очереди кандидатов.
- `POST /profiles/{telegram_id}/photo` - загрузить фото анкеты в MinIO/S3.
- `GET /photos?key=...` - получить фото анкеты из MinIO/S3.

### Interactions

- `POST /interactions/{telegram_id}/like` - лайкнуть текущего кандидата.
- `POST /interactions/{telegram_id}/skip` - пропустить текущего кандидата.

### Matches

- `GET /matches/{telegram_id}` - список мэтчей.
- `POST /matches/{telegram_id}/dialogs/{other_telegram_id}` - отметить начало диалога.

### Ratings

- `GET /ratings/{telegram_id}` - получить рейтинг пользователя.

### Likes

- `GET /likes/{telegram_id}` - последние исходящие лайки пользователя.

## Рейтинг

Рейтинг рассчитывается в `backend/ranking.py`.

Итоговая формула:

```text
final_score = 45% Level 1 + 45% Level 2 + 10% referral score
```

Level 1 оценивает заполненность анкеты:

- возраст;
- пол;
- город;
- интересы;
- описание;
- фото;
- предпочтения по полу;
- предпочтения по возрасту;
- предпочтения по городу.

Level 2 оценивает поведение:

- сколько лайков получила анкета;
- соотношение лайков и пропусков;
- количество мэтчей;
- количество начатых диалогов;
- недавняя активность.

Referral score начисляется за приглашенных пользователей.

## Redis-кэш кандидатов

При просмотре анкет backend не пересчитывает полный список кандидатов каждый раз. Он заранее формирует очередь подходящих пользователей и кладет ее в Redis.

Код находится в:

```text
backend/cache.py
```

Главные функции:

- `refill_candidate_queue`
- `get_or_load_current_candidate_id`
- `consume_current_candidate`
- `invalidate_candidate_cache`
- `invalidate_all_candidate_caches`

## MinIO / S3 для фотографий

Фотографии анкет хранятся в S3-совместимом хранилище MinIO.

Загрузка работает так:

1. Пользователь отправляет фото Telegram-боту.
2. Бот скачивает файл из Telegram.
3. Бот отправляет файл в backend endpoint `POST /profiles/{telegram_id}/photo`.
4. Backend сохраняет файл в bucket `dating-bot-photos`.
5. В анкете сохраняется ключ объекта, например `profiles/123456789/...jpg`.

Показ фото работает так:

1. Бот получает анкету с ключом фото.
2. Бот запрашивает `GET /photos?key=...`.
3. Backend читает объект из MinIO.
4. Бот отправляет байты изображения пользователю в Telegram.

Код находится в:

```text
backend/storage.py
backend/main.py
bot/bot.py
```

## Celery

Celery используется для задач, которые можно выполнять в фоне:

- пересчет рейтинга одного пользователя;
- пересчет рейтингов нескольких пользователей;
- периодический пересчет всех рейтингов;
- прогрев очередей кандидатов;
- heartbeat worker для healthcheck.

Код находится в:

```text
backend/tasks.py
backend/background.py
```

## RabbitMQ

RabbitMQ используется как брокер событий. Backend публикует события:

- `user_registered`
- `profile_liked`
- `profile_skipped`
- `dialog_started`

Эти события читает отдельный сервис `notification_service` через durable queue:

```text
dating.notifications
```

Поток:

```text
backend -> exchange dating.events -> queue dating.notifications -> notification_service -> Telegram
```

Notification service отправляет:

- уведомление о лайке пользователю, которого лайкнули;
- уведомление о мэтче;
- уведомление о начале диалога;
- уведомление пригласившему пользователю о регистрации по реферальной ссылке.

Код находится в:

```text
backend/events.py
backend/notification_service.py
```

## Метрики и логирование

Метрики доступны по адресу:

```text
http://localhost:8000/metrics
```

Собираются:

- количество HTTP-запросов;
- длительность HTTP-запросов;
- количество лайков и пропусков;
- информация о мэтчах в interaction-счетчике.
- средний итоговый рейтинг;
- средние Level 1, Level 2 и referral score;
- распределение пользователей по диапазонам рейтинга;
- количество пользователей, анкет, лайков, пропусков, мэтчей, диалогов;
- доля анкет с фотографией;
- состояние Redis-очередей кандидатов.

Логирование настраивается в:

```text
backend/logging_config.py
```

## Grafana

Grafana подключена через Docker Compose и автоматически получает Prometheus datasource и готовый dashboard.

Открыть Grafana:

```text
http://localhost:3000
```

Логин и пароль:

```text
admin / admin
```

Dashboard:

```text
Dating Bot / Dating Bot Overview
```

На dashboard есть:

- средний итоговый рейтинг;
- компоненты рейтинга Level 1, Level 2 и referral score;
- распределение пользователей по диапазонам рейтинга;
- количество пользователей и анкет;
- доля анкет с фотографиями;
- количество мэтчей и рефералов;
- match ratio;
- скорость лайков и пропусков;
- p95 latency API.

Файлы настройки:

```text
monitoring/prometheus.yml
monitoring/grafana/provisioning/datasources/prometheus.yml
monitoring/grafana/provisioning/dashboards/dashboards.yml
monitoring/grafana/dashboards/dating-bot-overview.json
```

## Тесты

Установка зависимостей:

```bash
pip install -r requirements.txt
```

Запуск тестов:

```bash
pytest -q
```

Тесты находятся в:

```text
tests/test_stage4.py
```

Они проверяют:

- реферальный бонус;
- создание неполной анкеты;
- получение кандидата;
- лайки;
- мэтчи;
- метрики;
- валидацию возрастного диапазона.

## CI

GitHub Actions workflow находится здесь:

```text
.github/workflows/ci.yml
```

Он устанавливает зависимости и запускает:

```bash
pytest -q
```

## Нагрузочное тестирование

Описание:

```text
docs/performance.md
```

JMeter-план:

```text
docs/stage4-load-test.jmx
```

Пример запуска:

```bash
jmeter -n -t docs/stage4-load-test.jmx -Jhost=localhost -Jport=8000 -Jthreads=25 -Jloops=20 -l load-results.jtl
```

## Проверка перед защитой

1. Убедиться, что `.env` заполнен.
2. Запустить проект:

```bash
docker compose up --build
```

3. Проверить:

```text
http://localhost:8000/docs
http://localhost:8000/health
http://localhost:8000/metrics
http://localhost:15672
http://localhost:9001
http://localhost:9090
http://localhost:3000
```

4. В Telegram пройти сценарий:

- `/start`;
- `Создать анкету`;
- `Пропустить поле` на нескольких шагах;
- `Смотреть анкеты`;
- `Лайк`;
- `Мои мэтчи`;
- `Мой рейтинг`;
- `Пригласить друга`.

5. Запустить тесты:

```bash
pytest -q
```
