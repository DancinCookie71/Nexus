"""Tests for storage/drive management endpoints."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.auth import create_user, grant_admin
from app.routes import storage as storage_routes


@pytest.fixture
def storage_user(db_session):
    return create_user(db_session, "storageadmin", "StrongPassword123!")


@pytest.fixture
def storage_auth_client(client, db_session, storage_user):
    from app.auth import create_session
    _, token = create_session(db_session, storage_user.id)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def storage_admin_client(client, db_session, storage_user):
    from app.auth import create_session
    session_obj, token = create_session(db_session, storage_user.id)
    grant_admin(db_session, session_obj)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def _sample_drive() -> dict:
    return {
        "device": "/dev/sda",
        "model": "Samsung SSD 860 EVO",
        "serial": "S123456789",
        "firmware": "RVT01B6Q",
        "size_bytes": 500107862016,
        "size_human": "465.8G",
        "rotation_rate": 0,
        "is_ssd": True,
        "smart_supported": True,
        "smart_enabled": True,
        "smart_status": "PASSED",
        "temperature_c": 30,
        "power_on_hours": 13317,
        "status": "healthy",
        "attributes": [],
        "messages": [],
    }


def test_list_drives(storage_admin_client, monkeypatch):
    monkeypatch.setattr(storage_routes, "list_drives", lambda: [])
    response = storage_admin_client.get("/api/v1/storage/drives")
    assert response.status_code == 200
    data = response.json()
    assert data["drives"] == []
    assert data["total"] == 0


def test_list_drives_requires_admin(storage_auth_client, monkeypatch):
    monkeypatch.setattr(storage_routes, "list_drives", lambda: [])
    response = storage_auth_client.get("/api/v1/storage/drives")
    assert response.status_code == 403


def test_examine_drive(storage_admin_client, monkeypatch):
    monkeypatch.setattr(storage_routes, "examine_drive", lambda device: type("Obj", (), _sample_drive())())

    response = storage_admin_client.get("/api/v1/storage/drives/%2Fdev%2Fsda")
    assert response.status_code == 200
    data = response.json()
    assert data["device"] == "/dev/sda"
    assert data["status"] == "healthy"


def test_examine_drive_requires_admin(storage_auth_client, monkeypatch):
    monkeypatch.setattr(storage_routes, "examine_drive", lambda device: type("Obj", (), _sample_drive())())
    response = storage_auth_client.get("/api/v1/storage/drives/%2Fdev%2Fsda")
    assert response.status_code == 403


def test_examine_drive_invalid(storage_admin_client):
    response = storage_admin_client.get("/api/v1/storage/drives/invalid;path")
    assert response.status_code == 400


def test_storage_requires_auth(client):
    response = client.get("/api/v1/storage/drives")
    assert response.status_code == 401

    response = client.get("/api/v1/storage/drives/%2Fdev%2Fsda")
    assert response.status_code == 401
