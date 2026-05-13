import os

os.environ["DATABASE_URL"] = "sqlite:///./test_dating_bot.sqlite3"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ["RABBITMQ_URL"] = "memory://"
os.environ["CELERY_BROKER_URL"] = "memory://"
os.environ["CELERY_RESULT_BACKEND"] = "cache+memory://"

import pytest
from fastapi.testclient import TestClient

from backend import cache, events
from backend.database import Base, engine
from backend.main import app


class InMemoryRedis:
    def __init__(self):
        self.values = {}
        self.lists = {}

    def ping(self):
        return True

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, ex=None):
        self.values[key] = str(value)
        return True

    def delete(self, *keys):
        deleted = 0
        for key in keys:
            if key in self.values:
                deleted += 1
                del self.values[key]
            if key in self.lists:
                deleted += 1
                del self.lists[key]
        return deleted

    def rpush(self, key, *values):
        self.lists.setdefault(key, [])
        self.lists[key].extend(str(value) for value in values)
        return len(self.lists[key])

    def lrange(self, key, start, end):
        values = self.lists.get(key, [])
        if end == -1:
            end = len(values) - 1
        return values[start : end + 1]

    def lpop(self, key):
        values = self.lists.get(key, [])
        return values.pop(0) if values else None

    def lindex(self, key, index):
        values = self.lists.get(key, [])
        try:
            return values[index]
        except IndexError:
            return None

    def llen(self, key):
        return len(self.lists.get(key, []))

    def scan_iter(self, pattern):
        prefix = pattern.rstrip("*")
        keys = set(self.values) | set(self.lists)
        for key in keys:
            if key.startswith(prefix):
                yield key


@pytest.fixture(autouse=True)
def isolated_app(monkeypatch):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    cache.redis_client = InMemoryRedis()
    monkeypatch.setattr(events, "publish_interaction_event", lambda *args, **kwargs: True)
    monkeypatch.setattr(events, "check_mq_connection", lambda: True)
    yield


@pytest.fixture
def client():
    return TestClient(app)


def register(client, telegram_id, username=None, referrer_telegram_id=None):
    response = client.post(
        "/users/register",
        json={
            "telegram_id": telegram_id,
            "username": username,
            "referrer_telegram_id": referrer_telegram_id,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["user"]


def create_profile(client, telegram_id, **overrides):
    payload = {
        "name": f"User {telegram_id}",
        "age": 25,
        "gender": "женщина",
        "city": "Москва",
        "interests": "кино, спорт, книги",
        "bio": "Люблю умные разговоры и прогулки.",
        "photo_url": f"telegram-file-{telegram_id}",
        "preferred_gender": None,
        "preferred_age_min": 18,
        "preferred_age_max": 35,
        "preferred_city": "Москва",
    }
    payload.update(overrides)
    response = client.post(f"/profiles/{telegram_id}", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_referral_bonus_is_counted_in_rating(client):
    inviter = register(client, "100", "alice")
    invitee = register(client, "200", "bob", referrer_telegram_id="100")

    assert invitee["referred_by_user_id"] == inviter["id"]

    response = client.get("/ratings/100")
    assert response.status_code == 200
    rating = response.json()
    assert rating["referral_score"] == 20.0
    assert rating["final_score"] > 0


def test_browse_like_match_and_metrics_flow(client):
    register(client, "100", "alice")
    register(client, "200", "bob")
    create_profile(client, "100", gender="женщина", preferred_gender="мужчина")
    create_profile(client, "200", gender="мужчина", preferred_gender="женщина")

    response = client.get("/profiles/100/candidate")
    assert response.status_code == 200
    assert response.json()["profile"]["name"] == "User 200"

    response = client.post("/interactions/100/like")
    assert response.status_code == 200
    assert response.json()["is_match"] is False

    response = client.post("/interactions/200/like")
    assert response.status_code == 200
    assert response.json()["is_match"] is True

    response = client.get("/matches/100")
    assert response.status_code == 200
    assert len(response.json()["matches"]) == 1

    response = client.get("/metrics")
    assert response.status_code == 200
    assert "dating_bot_http_requests_total" in response.text
    assert "dating_bot_interactions_total" in response.text


def test_profile_age_range_validation(client):
    register(client, "100", "alice")
    response = client.post(
        "/profiles/100",
        json={
            "name": "Alice",
            "age": 25,
            "gender": "женщина",
            "city": "Москва",
            "interests": "кино",
            "bio": "Тестовая анкета",
            "photo_url": "telegram-file-100",
            "preferred_age_min": 40,
            "preferred_age_max": 30,
        },
    )
    assert response.status_code == 422


def test_profile_can_be_created_with_skipped_fields(client):
    register(client, "300", "charlie")
    response = client.post(
        "/profiles/300",
        json={
            "name": "Charlie",
            "age": None,
            "gender": None,
            "city": None,
            "interests": None,
            "bio": None,
            "photo_url": None,
            "preferred_gender": None,
            "preferred_age_min": None,
            "preferred_age_max": None,
            "preferred_city": None,
        },
    )
    assert response.status_code == 201, response.text
    profile = response.json()
    assert profile["name"] == "Charlie"
    assert profile["age"] is None
    assert profile["photo_url"] is None

    rating_response = client.get("/ratings/300")
    assert rating_response.status_code == 200
    assert rating_response.json()["level1_score"] == 0.0
