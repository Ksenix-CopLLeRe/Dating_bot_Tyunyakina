# Dating Bot

Telegram dating bot with a FastAPI backend, PostgreSQL storage, Redis candidate
cache, RabbitMQ event bus and Celery background jobs.

## Stage 4 features

- Celery worker and beat tasks recalculate ratings, warm candidate queues and
  publish worker heartbeats.
- RabbitMQ receives domain events for registrations, likes, skips and dialog
  starts through the `dating.events` exchange.
- Redis stores pre-ranked candidate queues so browsing does not recompute the
  full recommendation list on every request.
- PostgreSQL schema includes indexes for profile matching, reactions, matches,
  dialogs and ratings.
- `/metrics` exposes Prometheus counters and histograms for API requests and
  interactions.
- Tests cover referral scoring, browsing, likes, matches, metrics and profile
  validation.
- GitHub Actions runs the test suite on every push or pull request.

## Local run

1. Copy `.env.example` to `.env` and set `BOT_TOKEN`.
2. Start the stack:

```bash
docker compose up --build
```

Services:

- backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- metrics: `http://localhost:8000/metrics`
- RabbitMQ UI: `http://localhost:15672` (`guest` / `guest`)

## Tests

```bash
pytest -q
```

The tests use SQLite, in-memory Redis and Celery eager mode, so they do not need
Docker services.
