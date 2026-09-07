"""Tests for admin privilege elevation endpoints."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.auth import create_user, grant_admin


@pytest.fixture
def admin_user(db_session):
    return create_user(db_session, "adminuser", "StrongPassword123!")


@pytest.fixture
def admin_auth_client(client, db_session, admin_user):
    from app.auth import create_session
    _, token = create_session(db_session, admin_user.id)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_admin_status_not_elevated(admin_auth_client):
    response = admin_auth_client.get("/api/v1/auth/admin")
    assert response.status_code == 200
    data = response.json()
    assert data["is_admin"] is False
    assert data["expires_at"] is None
    assert data["sudo_username"] is None


def test_elevate_admin_bad_password(admin_auth_client):
    with patch("app.routes.auth.verify_system_password", return_value=False):
        response = admin_auth_client.post("/api/v1/auth/admin", json={"username": "root", "password": "wrong"})
    assert response.status_code == 401


def test_elevate_admin_requires_sudoer(admin_auth_client):
    with (
        patch("app.routes.auth.verify_system_password", return_value=True),
        patch("app.routes.auth.is_unix_sudoer", return_value=False),
    ):
        response = admin_auth_client.post("/api/v1/auth/admin", json={"username": "plainuser", "password": "secret"})
    assert response.status_code == 403


def test_elevate_admin_success(admin_auth_client, db_session):
    with (
        patch("app.routes.auth.verify_system_password", return_value=True),
        patch("app.routes.auth.is_unix_sudoer", return_value=True),
    ):
        response = admin_auth_client.post("/api/v1/auth/admin", json={"username": "root", "password": "secret"})
    assert response.status_code == 200
    data = response.json()
    assert data["is_admin"] is True
    assert data["expires_at"] is not None
    assert data["username"] == "root"
    assert data["sudo_username"] == "root"


def test_revoke_admin(admin_auth_client, db_session):
    from app.auth import _hash_token, get_session_by_token
    token = admin_auth_client.headers["Authorization"].split()[1]
    session_obj = get_session_by_token(db_session, token)
    grant_admin(db_session, session_obj)
    response = admin_auth_client.delete("/api/v1/auth/admin")
    assert response.status_code == 200
    data = response.json()
    assert "revoked" in data["message"].lower()


def test_revoke_admin_without_grant(admin_auth_client):
    response = admin_auth_client.delete("/api/v1/auth/admin")
    assert response.status_code == 400


def test_admin_requires_auth(client):
    response = client.get("/api/v1/auth/admin")
    assert response.status_code == 401
    response = client.post("/api/v1/auth/admin", json={"username": "root", "password": "x"})
    assert response.status_code == 401
    response = client.delete("/api/v1/auth/admin")
    assert response.status_code == 401
