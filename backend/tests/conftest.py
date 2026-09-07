"""Pytest configuration and shared fixtures."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Set a deterministic secret key for tests.
os.environ["NEXUS_SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["NEXUS_DATABASE_URL"] = "sqlite:///./test.db"
os.environ["NEXUS_ENV"] = "development"
os.environ["NEXUS_SESSION_LIFETIME_MINUTES"] = "60"
os.environ["TERMINAL"] = "true"

from app import main  # noqa: E402
from app.auth import create_session, create_user  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.dependencies import admin_elevation_limiter, login_rate_limiter  # noqa: E402
from app.models import SessionToken  # noqa: E402
from app.services.settings import seed_defaults  # noqa: E402

engine = create_engine(
    "sqlite:///./test.db",
    connect_args={"check_same_thread": False},
    future=True,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        seed_defaults(db)
    finally:
        db.close()
    login_rate_limiter.reset()
    admin_elevation_limiter.reset()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    main.app.dependency_overrides[get_db] = override_get_db
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    return create_user(db_session, "testadmin", "StrongPassword123!")


@pytest.fixture
def auth_client(client, db_session, test_user):
    _, token = create_session(db_session, test_user.id)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
