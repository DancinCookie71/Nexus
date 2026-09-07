"""Tests for the detailed health monitoring endpoints."""
from __future__ import annotations

import pytest

from app.auth import create_user, grant_admin
from app.services.health import DriveHealthSummary, HealthSnapshot, calculate_overall_status


@pytest.fixture
def health_user(db_session):
    return create_user(db_session, "healthadmin", "StrongPassword123!")


@pytest.fixture
def health_auth_client(client, db_session, health_user):
    from app.auth import create_session
    _, token = create_session(db_session, health_user.id)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def health_admin_client(client, db_session, health_user):
    from app.auth import create_session
    session_obj, token = create_session(db_session, health_user.id)
    grant_admin(db_session, session_obj)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_live_health_requires_auth(client):
    response = client.get("/api/v1/health/live")
    assert response.status_code == 401


def test_live_health_snapshot(health_auth_client):
    response = health_auth_client.get("/api/v1/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["overall"] in {"healthy", "warning", "critical"}
    assert "cpu" in data
    assert "memory" in data
    assert "disks" in data
    assert "network" in data
    assert "uptime_seconds" in data
    # SMART drive summary is gated behind admin mode.
    assert data.get("drives") == []


def test_live_health_snapshot_admin_includes_drives(health_admin_client):
    response = health_admin_client.get("/api/v1/health/live")
    assert response.status_code == 200
    data = response.json()
    assert "drives" in data


def test_live_health_websocket_unauthenticated(client):
    with pytest.raises(Exception):
        with client.websocket_connect("/api/v1/health/live/ws") as ws:
            ws.receive()


def test_live_health_websocket_authenticated(health_auth_client, db_session, health_user):
    from app.auth import create_session
    _, token = create_session(db_session, health_user.id)
    with health_auth_client.websocket_connect(f"/api/v1/health/live/ws?token={token}") as ws:
        data = ws.receive_json()
        assert data["overall"] in {"healthy", "warning", "critical"}
        assert "cpu" in data


def test_smart_drive_failure_is_critical():
    snapshot = HealthSnapshot(
        drives=[DriveHealthSummary(
            device="/dev/sda",
            status="critical",
            smart_status="FAILED",
        )]
    )
    assert calculate_overall_status(snapshot) == "critical"
