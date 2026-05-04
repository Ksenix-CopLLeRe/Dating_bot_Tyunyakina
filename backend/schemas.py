from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserCreate(BaseModel):
    telegram_id: str
    username: str | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: str
    username: str | None = None
    created_at: datetime


class RegistrationResponse(BaseModel):
    user: UserResponse
    created: bool
    message: str


class HealthResponse(BaseModel):
    status: str
    database: str
    redis: str


class ProfileBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    age: int = Field(ge=18, le=100)
    gender: str = Field(min_length=1, max_length=32)
    city: str = Field(min_length=1, max_length=128)
    interests: str = Field(min_length=1, max_length=1000)
    bio: str = Field(min_length=1, max_length=2000)
    photo_url: str = Field(min_length=1, max_length=2048)
    preferred_gender: str | None = Field(default=None, max_length=32)
    preferred_age_min: int | None = Field(default=None, ge=18, le=100)
    preferred_age_max: int | None = Field(default=None, ge=18, le=100)
    preferred_city: str | None = Field(default=None, max_length=128)

    @field_validator(
        "gender",
        "city",
        "interests",
        "bio",
        "photo_url",
        "preferred_gender",
        "preferred_city",
        "name",
    )
    @classmethod
    def strip_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("preferred_age_max")
    @classmethod
    def validate_age_range(cls, preferred_age_max: int | None, info) -> int | None:
        preferred_age_min = info.data.get("preferred_age_min")
        if (
            preferred_age_min is not None
            and preferred_age_max is not None
            and preferred_age_max < preferred_age_min
        ):
            raise ValueError("preferred_age_max must be greater than or equal to preferred_age_min")
        return preferred_age_max


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    age: int | None = Field(default=None, ge=18, le=100)
    gender: str | None = Field(default=None, min_length=1, max_length=32)
    city: str | None = Field(default=None, min_length=1, max_length=128)
    interests: str | None = Field(default=None, min_length=1, max_length=1000)
    bio: str | None = Field(default=None, min_length=1, max_length=2000)
    photo_url: str | None = Field(default=None, min_length=1, max_length=2048)
    preferred_gender: str | None = Field(default=None, max_length=32)
    preferred_age_min: int | None = Field(default=None, ge=18, le=100)
    preferred_age_max: int | None = Field(default=None, ge=18, le=100)
    preferred_city: str | None = Field(default=None, max_length=128)

    @field_validator(
        "gender",
        "city",
        "interests",
        "bio",
        "photo_url",
        "preferred_gender",
        "preferred_city",
        "name",
    )
    @classmethod
    def strip_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("preferred_age_max")
    @classmethod
    def validate_partial_age_range(cls, preferred_age_max: int | None, info) -> int | None:
        preferred_age_min = info.data.get("preferred_age_min")
        if (
            preferred_age_min is not None
            and preferred_age_max is not None
            and preferred_age_max < preferred_age_min
        ):
            raise ValueError("preferred_age_max must be greater than or equal to preferred_age_min")
        return preferred_age_max


class RatingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    level1_score: float
    level2_score: float
    final_score: float
    updated_at: datetime


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str | None
    age: int | None
    gender: str | None
    city: str | None
    interests: str | None
    bio: str | None
    photo_url: str | None
    preferred_gender: str | None
    preferred_age_min: int | None
    preferred_age_max: int | None
    preferred_city: str | None
    created_at: datetime
    updated_at: datetime


class CandidateProfileResponse(BaseModel):
    user_id: int
    username: str | None = None
    profile: ProfileResponse
    rating: RatingResponse | None = None
    remaining_cached_candidates: int


class LikeNotificationResponse(BaseModel):
    recipient_telegram_id: str
    liker_username: str | None = None
    liker_profile: ProfileResponse | None = None


class MatchResponse(BaseModel):
    match_id: int
    other_user_id: int
    other_username: str | None = None
    profile: ProfileResponse | None = None
    created_at: datetime


class MatchListResponse(BaseModel):
    matches: list[MatchResponse]


class InteractionResponse(BaseModel):
    action: str
    target_user_id: int
    is_match: bool
    message: str
    next_candidate: CandidateProfileResponse | None = None
    like_notification: LikeNotificationResponse | None = None


class OutgoingLikeResponse(BaseModel):
    other_user_id: int
    other_username: str | None = None
    profile: ProfileResponse | None = None
    created_at: datetime
    is_match: bool


class OutgoingLikeListResponse(BaseModel):
    likes: list[OutgoingLikeResponse]


class QueueStateResponse(BaseModel):
    current_candidate_id: int | None
    remaining_cached_candidates: int


class MessageResponse(BaseModel):
    message: str
