"""Tests for UNIX account login and admin elevation lifetime."""
from __future__ import annotations

import pwd
from unittest.mock import patch

import pytest

from app.auth import (
    create_session,
    create_user,
    get_or_create_unix_user,
    is_real_unix_user,
    verify_password,
)
from app.models import User
from app.services.settings import set_setting


class _FakePwdEntry:
    def __init__(self, pw_uid, pw_shell):
        self.pw_uid = pw_uid
        self.pw_shell = pw_shell


@pytest.fixture
def fake_pwd(monkeypatch):
    users = {
        "exampleuser": _FakePwdEntry(1000, "/bin/bash"),
        "fishuser": _FakePwdEntry(1001, "/usr/bin/fish"),
        "www-data": _FakePwdEntry(33, "/usr/sbin/nologin"),
        "nexus": _FakePwdEntry(990, "/usr/sbin/nologin"),
        "root": _FakePwdEntry(0, "/bin/bash"),
    }

    def getpwnam(name):
        if name in users:
            return users[name]
        raise KeyError(name)

    monkeypatch.setattr(pwd, "getpwnam", getpwnam)
    return users


def test_is_real_unix_user_accepts_human_account(fake_pwd):
    assert is_real_unix_user("exampleuser") is True


def test_is_real_unix_user_accepts_nonstandard_shell(fake_pwd):
    assert is_real_unix_user("fishuser") is True


def test_is_real_unix_user_rejects_system_accounts(fake_pwd):
    assert is_real_unix_user("www-data") is False
    assert is_real_unix_user("nexus") is False
    assert is_real_unix_user("root") is False


def test_is_real_unix_user_rejects_unknown(fake_pwd):
    assert is_real_unix_user("ghost") is False


def test_is_real_unix_user_rejects_invalid_names(fake_pwd):
    assert is_real_unix_user("Bad Name") is False
    assert is_real_unix_user("") is False


def test_verify_password_invalid_hash_is_false():
    assert verify_password("whatever", "") is False


def test_get_or_create_unix_user_idempotent(db_session):
    first = get_or_create_unix_user(db_session, "exampleuser")
    second = get_or_create_unix_user(db_session, "exampleuser")
    assert first.id == second.id
    assert first.auth_source == "unix"


def test_unix_login_creates_panel_user(client, db_session):
    with patch("app.routes.auth.is_real_unix_user", return_value=True), patch(
        "app.routes.auth.verify_system_password", return_value=True
    ):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "exampleuser", "password": "secret"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["username"] == "exampleuser"
    user = db_session.query(User).filter(User.username == "exampleuser").first()
    assert user is not None
    assert user.auth_source == "unix"


def test_unix_login_wrong_password_rejected(client, db_session):
    with patch("app.routes.auth.is_real_unix_user", return_value=True), patch(
        "app.routes.auth.verify_system_password", return_value=False
    ):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "exampleuser", "password": "wrong"},
        )
    assert response.status_code == 401
    assert db_session.query(User).filter(User.username == "exampleuser").first() is None


def test_system_account_cannot_login(client, db_session):
    with patch("app.routes.auth.verify_system_password", return_value=True):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "www-data", "password": "secret"},
        )
    assert response.status_code == 401
    assert db_session.query(User).filter(User.username == "www-data").first() is None


def test_local_user_login_still_works(client, db_session):
    create_user(db_session, "testadmin", "StrongPassword123!")
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "testadmin", "password": "StrongPassword123!"},
    )
    assert response.status_code == 200
    user = db_session.query(User).filter(User.username == "testadmin").first()
    assert user.auth_source == "local"


def test_local_user_shadows_unix_account(client, db_session):
    create_user(db_session, "exampleuser", "PanelPassword123!")
    with patch(
        "app.routes.auth.verify_system_password",
        side_effect=AssertionError("must not be called"),
    ):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "exampleuser", "password": "PanelPassword123!"},
        )
    assert response.status_code == 200


def test_admin_grant_never_expires_when_lifetime_zero(client, db_session):
    set_setting(db_session, "admin_session_lifetime_minutes", "0")
    create_user(db_session, "admin2", "StrongPassword123!")
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "admin2", "password": "StrongPassword123!"},
    )
    assert login.status_code == 200
    with (
        patch("app.routes.auth.verify_system_password", return_value=True),
        patch("app.routes.auth.is_unix_sudoer", return_value=True),
    ):
        response = client.post(
            "/api/v1/auth/admin",
            json={"username": "admin2", "password": "secret"},
        )
    assert response.status_code == 200
    expires_at = response.json()["expires_at"]
    assert int(expires_at[:4]) >= 2100


def test_admin_grant_with_positive_lifetime(client, db_session):
    set_setting(db_session, "admin_session_lifetime_minutes", "15")
    create_user(db_session, "admin3", "StrongPassword123!")
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "admin3", "password": "StrongPassword123!"},
    )
    assert login.status_code == 200
    with (
        patch("app.routes.auth.verify_system_password", return_value=True),
        patch("app.routes.auth.is_unix_sudoer", return_value=True),
    ):
        response = client.post(
            "/api/v1/auth/admin",
            json={"username": "admin3", "password": "secret"},
        )
    assert response.status_code == 200
    expires_at = response.json()["expires_at"]
    assert int(expires_at[:4]) < 2100


def test_unix_login_session_works_end_to_end(client, db_session):
    with patch("app.routes.auth.is_real_unix_user", return_value=True), patch(
        "app.routes.auth.verify_system_password", return_value=True
    ):
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "exampleuser", "password": "secret"},
        )
    token = login.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "exampleuser"


def test_optional_operator_prefers_admin_username(db_session):
    from app.auth import grant_admin, get_session_by_token
    from app.dependencies import get_optional_admin_user

    user = get_or_create_unix_user(db_session, "exampleuser")
    session_obj, token = create_session(db_session, user.id)
    assert get_optional_admin_user(session=session_obj, db=db_session) == "exampleuser"
    grant_admin(db_session, session_obj, sudo_username="otheradmin")
    assert get_optional_admin_user(session=session_obj, db=db_session) == "otheradmin"


def test_optional_operator_none_for_local_user(db_session):
    from app.dependencies import get_optional_admin_user

    user = create_user(db_session, "testadmin", "StrongPassword123!")
    session_obj, _ = create_session(db_session, user.id)
    assert get_optional_admin_user(session=session_obj, db=db_session) is None


def test_terminal_resolves_unix_user(db_session):
    from app.routes.terminal import _resolve_terminal_user

    user = get_or_create_unix_user(db_session, "exampleuser")
    session_obj, _ = create_session(db_session, user.id)
    assert _resolve_terminal_user(db_session, session_obj) == "exampleuser"


def test_terminal_admin_username_wins(db_session):
    from app.auth import grant_admin
    from app.routes.terminal import _resolve_terminal_user

    user = get_or_create_unix_user(db_session, "exampleuser")
    session_obj, _ = create_session(db_session, user.id)
    grant_admin(db_session, session_obj, sudo_username="root")
    assert _resolve_terminal_user(db_session, session_obj) == "root"


def test_files_run_as_unix_user(client, db_session, monkeypatch):
    from app.services.files import list_directory

    with patch("app.routes.auth.is_real_unix_user", return_value=True), patch(
        "app.routes.auth.verify_system_password", return_value=True
    ):
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "exampleuser", "password": "secret"},
        )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    def fake_run_worker(admin_user, func, *args, **kwargs):
        return {"path": "", "entries": []}

    called = []
    monkeypatch.setattr(
        "app.services.files._run_worker",
        lambda admin_user, func, *a, **k: (called.append(admin_user), fake_run_worker(admin_user, func))[1],
    )
    response = client.get("/api/v1/files", headers=headers)
    assert response.status_code == 200
    assert called == ["exampleuser"]


def test_local_user_files_run_as_nexus(client, db_session, monkeypatch, tmp_path):
    from app.config import settings

    monkeypatch.setattr(settings, "files_root", str(tmp_path))
    (tmp_path / "note.txt").write_text("hi")
    create_user(db_session, "testadmin", "StrongPassword123!")
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "testadmin", "password": "StrongPassword123!"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    def fail(*args, **kwargs):
        raise AssertionError("worker must not run for local users")

    monkeypatch.setattr("app.services.files._run_worker", fail)
    response = client.get("/api/v1/files", headers=headers)
    assert response.status_code == 200
    assert any(e["name"] == "note.txt" for e in response.json()["entries"])


def test_reserved_usernames_cannot_login(client, db_session):
    create_user(db_session, "admin", "StrongPassword123!")
    for name in ("admin", "nexus", "root", "ADMIN", "Nexus", "Root"):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": name, "password": "StrongPassword123!"},
        )
        assert response.status_code == 401


def test_setup_rejects_reserved_username(client, db_session):
    response = client.post(
        "/api/v1/auth/setup",
        json={"username": "admin", "password": "StrongPassword123!"},
    )
    assert response.status_code == 400
