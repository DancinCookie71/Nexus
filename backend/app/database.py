"""Database setup and dependency injection."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.config import settings

# Ensure parent directory exists for relative SQLite paths.
settings.database_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Session:
    """Yield a database session for dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
