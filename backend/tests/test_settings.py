"""Tests for settings management endpoints."""
from __future__ import annotations

import pytest

from app.auth import create_user, grant_admin


@pytest.fixture
def settings_user(db_session):
    return create_user(db_session, "settingsuser", "StrongPassword123!")


@pytest.fixture
def settings_auth_client(client, db_session, settings_user):
    from app.auth import create_session
    _, token = create_session(db_session, settings_user.id)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def settings_admin_client(client, db_session, settings_user):
    from app.auth import create_session
    session_obj, token = create_session(db_session, settings_user.id)
    grant_admin(db_session, session_obj)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_list_settings_requires_auth(client):
    response = client.get("/api/v1/settings")
    assert response.status_code == 401


def test_list_settings(settings_auth_client):
    response = settings_auth_client.get("/api/v1/settings")
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    assert "nexus" in data["categories"]
    assert "app_name" in data["categories"]["nexus"]


def test_update_setting_requires_admin(settings_auth_client):
    response = settings_auth_client.put("/api/v1/settings/app_name", json={"value": "Test Panel"})
    assert response.status_code == 403


def test_update_setting(settings_admin_client):
    response = settings_admin_client.put("/api/v1/settings/app_name", json={"value": "Test Panel"})
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == "Test Panel"
    assert data["key"] == "app_name"


def test_update_unknown_setting(settings_admin_client):
    response = settings_admin_client.put("/api/v1/settings/does_not_exist", json={"value": "x"})
    assert response.status_code == 404
