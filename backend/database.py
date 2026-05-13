from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import (
    DATABASE_MAX_OVERFLOW,
    DATABASE_POOL_RECYCLE,
    DATABASE_POOL_SIZE,
    DATABASE_URL,
)


def build_engine_options() -> dict:
    if DATABASE_URL.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}

    return {
        "pool_pre_ping": True,
        "pool_size": DATABASE_POOL_SIZE,
        "max_overflow": DATABASE_MAX_OVERFLOW,
        "pool_recycle": DATABASE_POOL_RECYCLE,
    }


engine = create_engine(DATABASE_URL, **build_engine_options())

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
