"""API endpoint tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.auth import create_session, create_user
from app.models import SessionToken


def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "nexus-api"
    assert "version" in data


def test_unauthorized_system(client):
    response = client.get("/api/v1/system")
    assert response.status_code == 401
    assert "detail" in response.json()


def test_create_first_user(client):
    response = client.post("/api/v1/auth/setup", json={
        "username": "testadmin",
        "password": "StrongPassword123!",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testadmin"
    assert "password" not in data
    assert "password_hash" not in data


def test_create_first_user_already_exists(client, test_user):
    response = client.post("/api/v1/auth/setup", json={
        "username": "newadmin",
        "password": "StrongPassword123!",
    })
    assert response.status_code == 403


def test_login_success(client, test_user):
    response = client.post("/api/v1/auth/login", json={
        "username": "testadmin",
        "password": "StrongPassword123!",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data
    assert "expires_at" in data
    assert data["user"]["username"] == "testadmin"
    assert "nexus_session" in response.cookies


def test_login_invalid_credentials(client, test_user):
    response = client.post("/api/v1/auth/login", json={
        "username": "testadmin",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


def test_login_rate_limit(client, test_user):
    for _ in range(5):
        response = client.post("/api/v1/auth/login", json={
            "username": "testadmin",
            "password": "wrongpassword",
        })
        assert response.status_code == 401

    response = client.post("/api/v1/auth/login", json={
        "username": "testadmin",
        "password": "wrongpassword",
    })
    assert response.status_code == 429


def test_login_validation(client):
    response = client.post("/api/v1/auth/login", json={
        "username": "",
        "password": "",
    })
    assert response.status_code == 422


def test_me_authenticated(auth_client, test_user):
    response = auth_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testadmin"
    assert "id" in data


def test_me_unauthorized(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_system_authenticated(auth_client):
    response = auth_client.get("/api/v1/system")
    assert response.status_code == 200
    data = response.json()
    assert "cpu" in data
    assert "memory" in data
    assert "disk" in data
    assert "hostname" in data


def test_logout(auth_client):
    response = auth_client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert "nexus_session" not in response.cookies or response.cookies.get("nexus_session") == ""

    response = auth_client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_list_sessions(auth_client, test_user, db_session):
    # Create an extra session.
    create_session(db_session, test_user.id, user_agent="TestAgent")
    response = auth_client.get("/api/v1/auth/sessions")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_revoke_session(auth_client, test_user, db_session):
    session_obj, _ = create_session(db_session, test_user.id)
    response = auth_client.delete(f"/api/v1/auth/sessions/{session_obj.id}")
    assert response.status_code == 200

    # Ensure the session is revoked.
    revoked = db_session.query(SessionToken).filter_by(id=session_obj.id).first()
    assert revoked.revoked_at is not None


def test_revoke_other_user_session_forbidden(auth_client, db_session):
    other = create_user(db_session, "other", "StrongPassword123!")
    session_obj, _ = create_session(db_session, other.id)
    response = auth_client.delete(f"/api/v1/auth/sessions/{session_obj.id}")
    assert response.status_code == 404


def test_invalid_token(client):
    client.headers.update({"Authorization": "Bearer invalid-token"})
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_expired_session(client, db_session, test_user):
    session_obj, token = create_session(db_session, test_user.id)
    session_obj.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    client.headers.update({"Authorization": f"Bearer {token}"})
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_setup_password_too_short(client):
    response = client.post("/api/v1/auth/setup", json={
        "username": "testadmin",
        "password": "short",
    })
    assert response.status_code == 422
