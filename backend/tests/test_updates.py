"""Tests for update detection endpoint."""
from __future__ import annotations

import pytest

from app.auth import create_user
from app.routes import updates as updates_routes
from app.services.updates import UpdateResult


@pytest.fixture
def update_user(db_session):
    return create_user(db_session, "updateadmin", "StrongPassword123!")


@pytest.fixture
def update_auth_client(client, db_session, update_user):
    from app.auth import create_session, grant_admin
    session_obj, token = create_session(db_session, update_user.id)
    grant_admin(db_session, session_obj)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_get_updates(update_auth_client, monkeypatch):
    def mock_detect():
        return UpdateResult(
            supported=True,
            package_manager="apt",
            update_count=3,
            packages=["openssl", "curl", "linux-image"],
            error=None,
            last_checked="2026-09-05T00:00:00+00:00",
        )

    monkeypatch.setattr(updates_routes, "detect_updates", mock_detect)

    response = update_auth_client.get("/api/v1/updates")
    assert response.status_code == 200
    data = response.json()
    assert data["supported"] is True
    assert data["package_manager"] == "apt"
    assert data["update_count"] == 3
    assert len(data["packages"]) == 3


def test_get_updates_unsupported(update_auth_client, monkeypatch):
    def mock_detect():
        return UpdateResult(
            supported=False,
            package_manager=None,
            update_count=0,
            packages=[],
            error="No supported package manager detected.",
            last_checked=None,
        )

    monkeypatch.setattr(updates_routes, "detect_updates", mock_detect)

    response = update_auth_client.get("/api/v1/updates")
    assert response.status_code == 200
    data = response.json()
    assert data["supported"] is False
    assert data["error"] is not None


def test_apply_updates_requires_admin(update_auth_client, monkeypatch):
    def mock_apply(reboot=False):
        from app.services.updates import ApplyResult
        return ApplyResult(success=True, message="Updates installed.", reboot_scheduled=False)

    monkeypatch.setattr(updates_routes, "apply_updates", mock_apply)

    response = update_auth_client.post("/api/v1/updates", json={"reboot": False})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["reboot_scheduled"] is False


def test_apply_updates_reboot(update_auth_client, monkeypatch):
    def mock_apply(reboot=False):
        from app.services.updates import ApplyResult
        return ApplyResult(
            success=True,
            message="Updates installed. Rebooting.",
            reboot_scheduled=True,
        )

    monkeypatch.setattr(updates_routes, "apply_updates", mock_apply)

    response = update_auth_client.post("/api/v1/updates", json={"reboot": True})
    assert response.status_code == 200
    data = response.json()
    assert data["reboot_scheduled"] is True


def test_apply_updates_failure(update_auth_client, monkeypatch):
    def mock_apply(reboot=False):
        from app.services.updates import ApplyResult
        return ApplyResult(success=False, message="apt upgrade failed")

    monkeypatch.setattr(updates_routes, "apply_updates", mock_apply)

    response = update_auth_client.post("/api/v1/updates", json={})
    assert response.status_code == 500
    assert "apt upgrade failed" in response.json()["detail"]


def test_updates_require_auth(client):
    response = client.get("/api/v1/updates")
    assert response.status_code == 401

    response = client.post("/api/v1/updates", json={})
    assert response.status_code == 401
