"""Tests for page routes and navigation."""
from __future__ import annotations

import pytest

from app.auth import create_user


@pytest.fixture
def nav_user(db_session):
    return create_user(db_session, "navadmin", "StrongPassword123!")


@pytest.fixture
def nav_auth_client(client, db_session, nav_user):
    from app.auth import create_session
    _, token = create_session(db_session, nav_user.id)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


def test_root_redirects_to_overview(nav_auth_client):
    response = nav_auth_client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/overview"


def test_dashboard_redirects_to_overview(nav_auth_client):
    response = nav_auth_client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/overview"


@pytest.mark.parametrize("page", ["/overview", "/health", "/services", "/service-detail", "/storage", "/drive-detail", "/files", "/updates", "/terminal"])
def test_authenticated_pages_served(nav_auth_client, page):
    response = nav_auth_client.get(page)
    assert response.status_code == 200
    assert "Nexus Panel" in response.text


def test_login_page_public(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert "Sign in" in response.text or "Sign In" in response.text


@pytest.mark.parametrize("page", ["/overview", "/health", "/services", "/service-detail", "/storage", "/drive-detail", "/files", "/updates", "/terminal"])
def test_unauthenticated_pages_redirect_or_serve_html(client, page):
    # The backend serves the HTML shell; the frontend JS redirects.
    # We just verify the page is reachable.
    response = client.get(page)
    assert response.status_code == 200
    assert "Nexus Panel" in response.text
