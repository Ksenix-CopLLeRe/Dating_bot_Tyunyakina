from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    referred_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    profile = relationship(
        "Profile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    referrals_sent = relationship(
        "Referral",
        foreign_keys="Referral.inviter_user_id",
        back_populates="inviter",
        cascade="all, delete-orphan",
    )
    referral_received = relationship(
        "Referral",
        foreign_keys="Referral.invited_user_id",
        back_populates="invited",
        uselist=False,
    )
    rating = relationship(
        "Rating",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = (
        Index("ix_profiles_matching", "gender", "city", "age"),
        Index("ix_profiles_preferences", "preferred_gender", "preferred_city"),
        Index("ix_profiles_updated_at", "updated_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String(128), nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    city = Column(String, nullable=True)
    interests = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)
    photo_url = Column(String, nullable=True)
    preferred_gender = Column(String, nullable=True)
    preferred_age_min = Column(Integer, nullable=True)
    preferred_age_max = Column(Integer, nullable=True)
    preferred_city = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = relationship("User", back_populates="profile")


class Like(Base):
    __tablename__ = "likes"
    __table_args__ = (
        UniqueConstraint("from_user_id", "to_user_id", name="uq_likes_from_to"),
        Index("ix_likes_to_created", "to_user_id", "created_at"),
        Index("ix_likes_from_created", "from_user_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("user1_id", "user2_id", name="uq_matches_users"),
        Index("ix_matches_user1_created", "user1_id", "created_at"),
        Index("ix_matches_user2_created", "user2_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user1_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user2_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Skip(Base):
    __tablename__ = "skips"
    __table_args__ = (
        UniqueConstraint("from_user_id", "to_user_id", name="uq_skips_from_to"),
        Index("ix_skips_to_created", "to_user_id", "created_at"),
        Index("ix_skips_from_created", "from_user_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class DialogInitiation(Base):
    __tablename__ = "dialog_initiations"
    __table_args__ = (
        Index("ix_dialogs_from_created", "from_user_id", "created_at"),
        Index("ix_dialogs_match_created", "match_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (
        Index("ix_ratings_final_score", "final_score"),
        Index("ix_ratings_updated_at", "updated_at"),
    )

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    level1_score = Column(Float, default=0.0, nullable=False)
    level2_score = Column(Float, default=0.0, nullable=False)
    referral_score = Column(Float, default=0.0, nullable=False)
    final_score = Column(Float, default=0.0, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = relationship("User", back_populates="rating")


class Referral(Base):
    __tablename__ = "referrals"
    __table_args__ = (
        UniqueConstraint("invited_user_id", name="uq_referrals_invited_user"),
        Index("ix_referrals_inviter_created", "inviter_user_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    inviter_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    invited_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    inviter = relationship("User", foreign_keys=[inviter_user_id], back_populates="referrals_sent")
    invited = relationship("User", foreign_keys=[invited_user_id], back_populates="referral_received")
