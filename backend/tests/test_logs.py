"""Tests for the logs endpoint."""
from __future__ import annotations

import pytest

from app.auth import create_user
from app.routes import logs as logs_routes
from app.services.logs import LogEntry


@pytest.fixture
def logs_user(db_session):
    return create_user(db_session, "logsadmin", "StrongPassword123!")


@pytest.fixture
def logs_auth_client(client, db_session, logs_user):
    from app.auth import create_session, grant_admin
    session_obj, token = create_session(db_session, logs_user.id)
    grant_admin(db_session, session_obj)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_get_logs(logs_auth_client, monkeypatch):
    def mock_read(unit, limit=200, since=None, until=None, priority=None):
        return [
            LogEntry(
                timestamp="2026-09-05T12:00:00+00:00",
                priority=6,
                priority_name="info",
                unit=unit,
                identifier="nginx",
                message="started",
            )
        ]

    monkeypatch.setattr(logs_routes, "journalctl_available", lambda: True)
    monkeypatch.setattr(logs_routes, "read_logs", mock_read)

    response = logs_auth_client.get("/api/v1/logs/nginx.service")
    assert response.status_code == 200
    data = response.json()
    assert data["unit"] == "nginx.service"
    assert len(data["entries"]) == 1
    assert data["entries"][0]["message"] == "started"


def test_get_logs_invalid_unit(logs_auth_client, monkeypatch):
    monkeypatch.setattr(logs_routes, "journalctl_available", lambda: True)

    response = logs_auth_client.get("/api/v1/logs/invalid;name.service")
    assert response.status_code == 400


def test_get_logs_journalctl_missing(logs_auth_client, monkeypatch):
    monkeypatch.setattr(logs_routes, "journalctl_available", lambda: False)

    response = logs_auth_client.get("/api/v1/logs/nginx.service")
    assert response.status_code == 503


def test_logs_require_auth(client):
    response = client.get("/api/v1/logs/nginx.service")
    assert response.status_code == 401
