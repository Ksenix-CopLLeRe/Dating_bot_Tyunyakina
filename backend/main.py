from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from . import cache, crud, schemas
from .database import Base, SessionLocal, engine
from .ranking import recompute_many, recompute_rating


Base.metadata.create_all(bind=engine)


def ensure_profile_schema() -> None:
    inspector = inspect(engine)
    profile_columns = {column["name"] for column in inspector.get_columns("profiles")}
    if "name" not in profile_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE profiles ADD COLUMN name VARCHAR(128)"))


ensure_profile_schema()

app = FastAPI(
    title="Dating Bot Backend",
    description="Backend API for the dating bot project.",
    version="0.3.0",
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_or_404(db: Session, telegram_id: str):
    user = crud.get_user_by_telegram(db, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден.")
    return user


def get_profile_or_404(db: Session, user_id: int):
    profile = crud.get_profile_by_user_id(db, user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Анкета не найдена.")
    return profile


def build_candidate_response(db: Session, viewer_user_id: int, candidate_user_id: int) -> schemas.CandidateProfileResponse:
    candidate_profile = crud.get_profile_by_user_id(db, candidate_user_id)
    if not candidate_profile:
        raise HTTPException(status_code=404, detail="Анкета кандидата не найдена.")

    candidate_user = crud.get_user_by_id(db, candidate_user_id)
    candidate_rating = crud.get_rating(db, candidate_user_id)
    queue_state = cache.queue_state(viewer_user_id)

    return schemas.CandidateProfileResponse(
        user_id=candidate_user_id,
        username=candidate_user.username if candidate_user else None,
        profile=candidate_profile,
        rating=candidate_rating,
        remaining_cached_candidates=queue_state["remaining_cached_candidates"],
    )


def build_like_notification(
    db: Session,
    liker_user_id: int,
    recipient_user_id: int,
) -> schemas.LikeNotificationResponse | None:
    recipient_user = crud.get_user_by_id(db, recipient_user_id)
    liker_user = crud.get_user_by_id(db, liker_user_id)
    liker_profile = crud.get_profile_by_user_id(db, liker_user_id)
    if not recipient_user or not liker_profile:
        return None

    return schemas.LikeNotificationResponse(
        recipient_telegram_id=recipient_user.telegram_id,
        liker_username=liker_user.username if liker_user else None,
        liker_profile=liker_profile,
    )


def get_next_candidate_response(db: Session, user_id: int) -> schemas.CandidateProfileResponse | None:
    candidate_user_id = cache.get_or_load_current_candidate_id(db, user_id)
    if candidate_user_id is None:
        return None
    return build_candidate_response(db, user_id, candidate_user_id)


@app.get("/", tags=["system"])
def root():
    return {
        "service": "dating-bot-backend",
        "status": "ok",
        "stage": "3",
    }


@app.get("/health", response_model=schemas.HealthResponse, tags=["system"])
def healthcheck(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    cache.redis_client.ping()
    return schemas.HealthResponse(status="ok", database="connected", redis="connected")


@app.post("/users/register", response_model=schemas.RegistrationResponse, tags=["users"])
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user, created = crud.get_or_create_user(db, user.telegram_id, user.username)
    recompute_rating(db, db_user.id)
    message = "Пользователь зарегистрирован." if created else "Пользователь уже зарегистрирован."
    return schemas.RegistrationResponse(user=db_user, created=created, message=message)


@app.get(
    "/users/by-telegram/{telegram_id}",
    response_model=schemas.UserResponse,
    tags=["users"],
)
def get_user_by_telegram(telegram_id: str, db: Session = Depends(get_db)):
    return get_user_or_404(db, telegram_id)


@app.post(
    "/profiles/{telegram_id}",
    response_model=schemas.ProfileResponse,
    status_code=201,
    tags=["profiles"],
)
def create_profile(
    telegram_id: str,
    profile: schemas.ProfileCreate,
    db: Session = Depends(get_db),
):
    user = get_user_or_404(db, telegram_id)
    existing_profile = crud.get_profile_by_user_id(db, user.id)
    if existing_profile:
        if crud.profile_has_content(existing_profile):
            raise HTTPException(status_code=409, detail="Анкета уже существует.")
        created_profile = crud.update_profile(db, existing_profile, profile.model_dump())
    else:
        created_profile = crud.create_profile(db, user.id, profile.model_dump())

    recompute_rating(db, user.id)
    cache.invalidate_candidate_cache(user.id)
    return created_profile


@app.get(
    "/profiles/{telegram_id}",
    response_model=schemas.ProfileResponse,
    tags=["profiles"],
)
def get_own_profile(telegram_id: str, db: Session = Depends(get_db)):
    user = get_user_or_404(db, telegram_id)
    return get_profile_or_404(db, user.id)


@app.put(
    "/profiles/{telegram_id}",
    response_model=schemas.ProfileResponse,
    tags=["profiles"],
)
def update_own_profile(
    telegram_id: str,
    profile_update: schemas.ProfileUpdate,
    db: Session = Depends(get_db),
):
    user = get_user_or_404(db, telegram_id)
    profile = get_profile_or_404(db, user.id)
    payload = profile_update.model_dump(exclude_unset=True)

    if not payload:
        raise HTTPException(status_code=400, detail="Нет данных для обновления.")

    updated_profile = crud.update_profile(db, profile, payload)
    recompute_rating(db, user.id)
    cache.invalidate_candidate_cache(user.id)
    return updated_profile


@app.delete(
    "/profiles/{telegram_id}",
    response_model=schemas.MessageResponse,
    tags=["profiles"],
)
def delete_own_profile(telegram_id: str, db: Session = Depends(get_db)):
    user = get_user_or_404(db, telegram_id)
    profile = get_profile_or_404(db, user.id)
    crud.delete_profile(db, profile)
    recompute_rating(db, user.id)
    cache.invalidate_candidate_cache(user.id)
    return schemas.MessageResponse(message="Анкета удалена.")


@app.get(
    "/profiles/{telegram_id}/candidate",
    response_model=schemas.CandidateProfileResponse,
    tags=["profiles"],
)
def get_candidate_profile(telegram_id: str, db: Session = Depends(get_db)):
    user = get_user_or_404(db, telegram_id)
    get_profile_or_404(db, user.id)

    candidate = get_next_candidate_response(db, user.id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Подходящие анкеты не найдены.")
    return candidate


@app.get(
    "/profiles/{telegram_id}/queue-state",
    response_model=schemas.QueueStateResponse,
    tags=["profiles"],
)
def get_queue_state(telegram_id: str, db: Session = Depends(get_db)):
    user = get_user_or_404(db, telegram_id)
    get_profile_or_404(db, user.id)
    cache.get_or_load_current_candidate_id(db, user.id)
    return schemas.QueueStateResponse(**cache.queue_state(user.id))


@app.get(
    "/ratings/{telegram_id}",
    response_model=schemas.RatingResponse,
    tags=["ratings"],
)
def get_rating(telegram_id: str, db: Session = Depends(get_db)):
    user = get_user_or_404(db, telegram_id)
    return recompute_rating(db, user.id)


@app.get(
    "/likes/{telegram_id}",
    response_model=schemas.OutgoingLikeListResponse,
    tags=["likes"],
)
def get_my_likes(
    telegram_id: str,
    limit: int = Query(default=10, ge=1, le=20),
    db: Session = Depends(get_db),
):
    user = get_user_or_404(db, telegram_id)
    likes = crud.get_recent_outgoing_likes(db, user.id, limit)

    result = []
    for like in likes:
        other_user = crud.get_user_by_id(db, like.to_user_id)
        other_profile = crud.get_profile_by_user_id(db, like.to_user_id)
        result.append(
            schemas.OutgoingLikeResponse(
                other_user_id=like.to_user_id,
                other_username=other_user.username if other_user else None,
                profile=other_profile,
                created_at=like.created_at,
                is_match=crud.get_match_between_users(db, user.id, like.to_user_id) is not None,
            )
        )

    return schemas.OutgoingLikeListResponse(likes=result)


@app.post(
    "/interactions/{telegram_id}/like",
    response_model=schemas.InteractionResponse,
    tags=["interactions"],
)
def like_current_candidate(telegram_id: str, db: Session = Depends(get_db)):
    user = get_user_or_404(db, telegram_id)
    get_profile_or_404(db, user.id)

    candidate_user_id = cache.consume_current_candidate(user.id)
    if candidate_user_id is None:
        candidate_user_id = cache.get_or_load_current_candidate_id(db, user.id)
    if candidate_user_id is None:
        raise HTTPException(status_code=404, detail="Нет доступной анкеты для лайка.")

    _like, created = crud.record_like(db, user.id, candidate_user_id)
    is_match = False
    if crud.is_mutual_like(db, user.id, candidate_user_id):
        crud.create_match(db, user.id, candidate_user_id)
        is_match = True

    recompute_many(db, [user.id, candidate_user_id])

    if cache.queue_state(user.id)["remaining_cached_candidates"] <= 1:
        cache.refill_candidate_queue(db, user.id)

    next_candidate = get_next_candidate_response(db, user.id)
    like_notification = build_like_notification(db, user.id, candidate_user_id) if created else None
    message = "Взаимный лайк! У вас мэтч." if is_match else "Лайк сохранен."
    return schemas.InteractionResponse(
        action="like",
        target_user_id=candidate_user_id,
        is_match=is_match,
        message=message,
        next_candidate=next_candidate,
        like_notification=like_notification,
    )


@app.post(
    "/interactions/{telegram_id}/skip",
    response_model=schemas.InteractionResponse,
    tags=["interactions"],
)
def skip_current_candidate(telegram_id: str, db: Session = Depends(get_db)):
    user = get_user_or_404(db, telegram_id)
    get_profile_or_404(db, user.id)

    candidate_user_id = cache.consume_current_candidate(user.id)
    if candidate_user_id is None:
        candidate_user_id = cache.get_or_load_current_candidate_id(db, user.id)
    if candidate_user_id is None:
        raise HTTPException(status_code=404, detail="Нет доступной анкеты для пропуска.")

    crud.record_skip(db, user.id, candidate_user_id)
    recompute_many(db, [user.id, candidate_user_id])

    if cache.queue_state(user.id)["remaining_cached_candidates"] <= 1:
        cache.refill_candidate_queue(db, user.id)

    next_candidate = get_next_candidate_response(db, user.id)
    return schemas.InteractionResponse(
        action="skip",
        target_user_id=candidate_user_id,
        is_match=False,
        message="Анкета пропущена.",
        next_candidate=next_candidate,
    )


@app.get(
    "/matches/{telegram_id}",
    response_model=schemas.MatchListResponse,
    tags=["matches"],
)
def get_matches(telegram_id: str, db: Session = Depends(get_db)):
    user = get_user_or_404(db, telegram_id)
    matches = crud.get_matches_for_user(db, user.id)

    result = []
    for match in matches:
        other_user_id = match.user2_id if match.user1_id == user.id else match.user1_id
        other_user = crud.get_user_by_id(db, other_user_id)
        other_profile = crud.get_profile_by_user_id(db, other_user_id)
        result.append(
            schemas.MatchResponse(
                match_id=match.id,
                other_user_id=other_user_id,
                other_username=other_user.username if other_user else None,
                profile=other_profile,
                created_at=match.created_at,
            )
        )

    return schemas.MatchListResponse(matches=result)


@app.post(
    "/matches/{telegram_id}/dialogs/{other_telegram_id}",
    response_model=schemas.MessageResponse,
    tags=["matches"],
)
def initiate_dialog(telegram_id: str, other_telegram_id: str, db: Session = Depends(get_db)):
    user = get_user_or_404(db, telegram_id)
    other_user = get_user_or_404(db, other_telegram_id)
    match = crud.get_match_between_users(db, user.id, other_user.id)
    if not match:
        raise HTTPException(status_code=404, detail="Мэтч между пользователями не найден.")

    crud.record_dialog_initiation(db, match.id, user.id, other_user.id)
    recompute_many(db, [user.id, other_user.id])
    return schemas.MessageResponse(message="Факт начала диалога сохранен.")
