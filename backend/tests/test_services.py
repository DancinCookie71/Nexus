"""Tests for service management endpoints."""
from __future__ import annotations

import pytest

from app.auth import create_user, grant_admin
from app.models import ServiceActionLog
from app.routes import services as services_routes
from app.schemas.services import ServiceDetail, ServiceSummary


@pytest.fixture
def service_user(db_session):
    return create_user(db_session, "serviceadmin", "StrongPassword123!")


@pytest.fixture
def service_auth_client(client, db_session, service_user):
    from app.auth import create_session
    _, token = create_session(db_session, service_user.id)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def service_admin_client(client, db_session, service_user):
    from app.auth import create_session
    session_obj, token = create_session(db_session, service_user.id)
    grant_admin(db_session, session_obj)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def _sample_summary(name: str = "nginx.service") -> ServiceSummary:
    return ServiceSummary(
        name=name,
        description="A high performance web server",
        load_state="loaded",
        active_state="active",
        sub_state="running",
        unit_file_state="enabled",
        main_pid=1234,
        memory_current=1024000,
        cpu_usage_nsec=500000000,
        tasks_current=5,
        is_system_service=False,
    )


def _sample_detail(name: str = "nginx.service") -> ServiceDetail:
    summary = _sample_summary(name)
    return ServiceDetail(
        **summary.model_dump(),
        names=[name],
        fragment_path=f"/lib/systemd/system/{name}",
        drop_in_paths=[],
        requires=[],
        wants=[],
        binds_to=[],
        part_of=[],
        conflicts=[],
        before=[],
        after=["network.target"],
        on_failure=[],
        can_start=True,
        can_stop=True,
        can_restart=True,
        can_reload=True,
    )


def test_list_services(service_auth_client, monkeypatch):
    monkeypatch.setattr(services_routes, "systemctl_available", lambda: True)
    monkeypatch.setattr(services_routes, "list_services", lambda **kwargs: [_sample_summary()])

    response = service_auth_client.get("/api/v1/services")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["services"]) == 1
    assert data["services"][0]["name"] == "nginx.service"


def test_list_services_filter(service_auth_client, monkeypatch):
    monkeypatch.setattr(services_routes, "systemctl_available", lambda: True)
    monkeypatch.setattr(services_routes, "list_services", lambda **kwargs: [_sample_summary("nginx.service")])

    response = service_auth_client.get("/api/v1/services?search=nginx")
    assert response.status_code == 200
    data = response.json()
    assert data["search"] == "nginx"


def test_list_services_systemctl_missing(service_auth_client, monkeypatch):
    monkeypatch.setattr(services_routes, "systemctl_available", lambda: False)

    response = service_auth_client.get("/api/v1/services")
    assert response.status_code == 503


def test_get_service_detail(service_auth_client, monkeypatch):
    monkeypatch.setattr(services_routes, "systemctl_available", lambda: True)
    monkeypatch.setattr(services_routes, "get_service_detail", lambda name: _sample_detail(name))

    response = service_auth_client.get("/api/v1/services/nginx.service")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "nginx.service"
    assert data["fragment_path"]


def test_service_action(service_admin_client, monkeypatch, db_session):
    monkeypatch.setattr(services_routes, "systemctl_available", lambda: True)
    monkeypatch.setattr(
        services_routes,
        "perform_service_action",
        lambda service, action: (True, "done"),
    )
    monkeypatch.setattr(services_routes, "get_service_detail", lambda name: _sample_detail(name))

    response = service_admin_client.post("/api/v1/services/nginx.service/restart")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["action"] == "restart"

    logs = db_session.query(ServiceActionLog).all()
    assert len(logs) == 1
    assert logs[0].service_name == "nginx.service"


def test_service_action_requires_admin(service_auth_client, monkeypatch):
    monkeypatch.setattr(services_routes, "systemctl_available", lambda: True)

    response = service_auth_client.post("/api/v1/services/nginx.service/restart")
    assert response.status_code == 403


def test_service_action_invalid(service_admin_client, monkeypatch):
    monkeypatch.setattr(services_routes, "systemctl_available", lambda: True)
    response = service_admin_client.post("/api/v1/services/nginx.service/destroy")
    assert response.status_code == 400


def test_services_require_auth(client):
    response = client.get("/api/v1/services")
    assert response.status_code == 401

    response = client.post("/api/v1/services/nginx.service/restart")
    assert response.status_code == 401
