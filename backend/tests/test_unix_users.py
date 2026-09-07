"""Tests for the Cockpit-style users system, sudoer auto-admin, and update commands."""
from __future__ import annotations

import pytest

from app.auth import (
    create_session,
    get_or_create_unix_user,
    is_unix_sudoer,
)
from app.services.users import (
    UserManagementError,
    create_unix_user,
    delete_unix_user,
    list_unix_users,
    set_admin_membership,
    set_unix_password,
)


def test_is_unix_sudoer_true_for_sudo_member(monkeypatch):
    import grp
    import pwd

    monkeypatch.setattr(
        pwd,
        "getpwnam",
        lambda name: type("E", (), {"pw_name": name, "pw_gid": 1000}),
    )
    monkeypatch.setattr(
        grp,
        "getgrnam",
        lambda name: type("G", (), {"gr_name": name, "gr_mem": ["sudouser"], "gr_gid": 27}),
    )
    assert is_unix_sudoer("sudouser") is True
    assert is_unix_sudoer("plainuser") is False
    assert is_unix_sudoer("ghost") is False


def _fake_entry(name, uid, gid, shell, home, gecos=""):
    return type(
        "E",
        (),
        {"pw_name": name, "pw_uid": uid, "pw_gid": gid, "pw_shell": shell, "pw_dir": home, "pw_gecos": gecos},
    )()


def _mock_passwd(monkeypatch):
    import pwd

    entries = [
        _fake_entry("root", 0, 0, "/bin/bash", "/root"),
        _fake_entry("www-data", 33, 33, "/usr/sbin/nologin", "/var/www"),
        _fake_entry("nexus", 995, 995, "/usr/sbin/nologin", "/home/nexus"),
        _fake_entry("exampleuser", 1000, 1000, "/bin/bash", "/home/exampleuser", "Example User"),
        _fake_entry("plainuser", 1001, 1001, "/bin/sh", "/home/plainuser"),
    ]
    monkeypatch.setattr(pwd, "getpwall", lambda: entries)
    return entries


def test_list_unix_users_filters_system_accounts(monkeypatch):
    import grp

    def fake_group(name):
        return type("G", (), {"gr_name": name, "gr_mem": ["exampleuser"], "gr_gid": 27})()

    monkeypatch.setattr(grp, "getgrnam", fake_group)
    _mock_passwd(monkeypatch)
    users = list_unix_users()
    usernames = [u["username"] for u in users]
    assert "exampleuser" in usernames
    assert "www-data" not in usernames
    assert "nexus" not in usernames
    me = next(u for u in users if u["username"] == "exampleuser")
    assert me["is_admin"] is True
    assert me["home"] == "/home/exampleuser"


def _assert_no_run(calls):
    raise AssertionError(f"sudo must not run for validation errors: {calls}")


def test_create_user_reserved_name_blocked(monkeypatch):
    monkeypatch.setattr("app.services.users._run", _assert_no_run)
    with pytest.raises(UserManagementError):
        create_unix_user("nexus", "", "StrongPassword1!")


def test_create_user_invalid_username_blocked(monkeypatch):
    monkeypatch.setattr("app.services.users._run", _assert_no_run)
    with pytest.raises(UserManagementError):
        create_unix_user("Bad Name", "", "StrongPassword1!")


def test_create_user_short_password_blocked(monkeypatch):
    monkeypatch.setattr("app.services.users._run", _assert_no_run)
    with pytest.raises(UserManagementError):
        create_unix_user("newbie", "", "short")


def test_create_user_existing_blocked(monkeypatch):
    import pwd

    monkeypatch.setattr("app.services.users._run", _assert_no_run)
    monkeypatch.setattr(
        pwd,
        "getpwnam",
        lambda username: _fake_entry("exampleuser", 1000, 1000, "/bin/bash", "/home/exampleuser"),
    )
    with pytest.raises(UserManagementError):
        create_unix_user("exampleuser", "", "StrongPassword1!")


def test_create_user_bad_shell_blocked(monkeypatch):
    monkeypatch.setattr("app.services.users._run", _assert_no_run)
    with pytest.raises(UserManagementError):
        create_unix_user("newbie", "", "StrongPassword1!", shell="/bin/evil")


def test_create_user_runs_expected_commands(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.services.users._run",
        lambda cmd, input_text=None, timeout=30: calls.append((cmd, input_text)),
    )
    monkeypatch.setattr("app.services.users._get_entry", lambda username: None)
    create_unix_user("newbie", "New Bie", "StrongPassword1!", "/bin/bash")
    assert calls[0][0] == ["useradd", "-m", "-c", "New Bie", "-s", "/bin/bash", "newbie"]
    assert calls[1][0] == ["chpasswd"]
    assert calls[1][1] == "newbie:StrongPassword1!\n"


def test_create_user_cleans_up_on_password_failure(monkeypatch):
    calls = []

    def fake_run(cmd, input_text=None, timeout=30):
        calls.append((cmd, input_text))
        if cmd[0] == "chpasswd":
            raise UserManagementError("chpasswd failed")

    monkeypatch.setattr("app.services.users._run", fake_run)
    with pytest.raises(UserManagementError):
        create_unix_user("newbie", "", "StrongPassword1!")
    assert calls[-1][0][0] == "userdel"


def test_set_password_validations(monkeypatch):
    monkeypatch.setattr("app.services.users._run", _assert_no_run)
    with pytest.raises(UserManagementError):
        set_unix_password("ghost", "StrongPassword1!")
    with pytest.raises(UserManagementError):
        set_unix_password("exampleuser", "short")


def test_set_password_runs_chpasswd(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.services.users._run",
        lambda cmd, input_text=None, timeout=30: calls.append((cmd, input_text)),
    )
    monkeypatch.setattr(
        "app.services.users._get_entry",
        lambda username: _fake_entry("exampleuser", 1000, 1000, "/bin/bash", "/home/exampleuser"),
    )
    set_unix_password("exampleuser", "StrongPassword1!")
    assert calls == [(["chpasswd"], "exampleuser:StrongPassword1!\n")]


def test_delete_self_blocked(monkeypatch):
    monkeypatch.setattr("app.services.users._run", _assert_no_run)
    with pytest.raises(UserManagementError):
        delete_unix_user("exampleuser", "exampleuser")


def test_delete_unknown_user_blocked(monkeypatch):
    monkeypatch.setattr("app.services.users._run", _assert_no_run)
    with pytest.raises(UserManagementError):
        delete_unix_user("ghost", "exampleuser")


def test_delete_runs_userdel(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.services.users._run",
        lambda cmd, input_text=None, timeout=30: calls.append(cmd),
    )
    monkeypatch.setattr("app.services.users._get_entry", lambda username: None)
    delete_unix_user("olduser", "exampleuser")
    assert calls == [["userdel", "olduser"]]


def test_admin_toggle_self_demote_blocked(monkeypatch):
    monkeypatch.setattr("app.services.users._run", _assert_no_run)
    with pytest.raises(UserManagementError):
        set_admin_membership("exampleuser", False, "exampleuser")


def test_admin_toggle_commands(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.services.users._run",
        lambda cmd, input_text=None, timeout=30: calls.append(cmd),
    )
    monkeypatch.setattr("app.services.users._get_entry", lambda username: None)
    set_admin_membership("newbie", True, "exampleuser")
    set_admin_membership("newbie", False, "exampleuser")
    assert calls == [
        ["usermod", "-aG", "sudo", "newbie"],
        ["usermod", "-rG", "sudo", "newbie"],
    ]


def test_require_admin_allows_unix_sudoer(db_session, monkeypatch):
    from app.auth import grant_admin
    from app.dependencies import require_admin
    from fastapi import HTTPException

    user = get_or_create_unix_user(db_session, "sudoguy")
    monkeypatch.setattr("app.dependencies.is_unix_sudoer", lambda username: username == "sudoguy")
    session_obj, _ = create_session(db_session, user.id)
    assert require_admin(session=session_obj, db=db_session) is session_obj

    plain = get_or_create_unix_user(db_session, "plainguy")
    plain_session, _ = create_session(db_session, plain.id)
    with pytest.raises(HTTPException) as exc:
        require_admin(session=plain_session, db=db_session)
    assert exc.value.status_code == 403

    elevated = get_or_create_unix_user(db_session, "elevated")
    elevated_session, _ = create_session(db_session, elevated.id)
    monkeypatch.setattr("app.auth.is_unix_sudoer", lambda username: False)
    grant_admin(db_session, elevated_session, sudo_username="root")
    assert require_admin(session=elevated_session, db=db_session) is elevated_session


def test_admin_status_reflects_implicit_admin(client, db_session, monkeypatch):
    user = get_or_create_unix_user(db_session, "sudoguy")
    monkeypatch.setattr("app.routes.auth.is_unix_sudoer", lambda username: username == "sudoguy")
    _, token = create_session(db_session, user.id)
    response = client.get("/api/v1/auth/admin", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["is_admin"] is True
    assert data["sudo_username"] == "sudoguy"
    assert data["expires_at"] is None


def test_users_api_requires_admin(client, db_session, monkeypatch):
    user = get_or_create_unix_user(db_session, "plainguy")
    monkeypatch.setattr("app.auth.is_unix_sudoer", lambda username: False)
    _, token = create_session(db_session, user.id)
    response = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_users_api_list_for_sudoer(client, db_session, monkeypatch):
    import grp

    def fake_group(name):
        return type("G", (), {"gr_name": name, "gr_mem": ["exampleuser"], "gr_gid": 27})()

    monkeypatch.setattr(grp, "getgrnam", fake_group)
    _mock_passwd(monkeypatch)
    user = get_or_create_unix_user(db_session, "sudoguy")
    monkeypatch.setattr("app.dependencies.is_unix_sudoer", lambda username: username == "sudoguy")
    _, token = create_session(db_session, user.id)
    response = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    usernames = [u["username"] for u in response.json()]
    assert "exampleuser" in usernames


def test_updates_use_sudoers_exact_commands(monkeypatch):
    from app.services import updates as updates_service

    calls = []

    def fake_run(cmd, timeout=120):
        calls.append(list(cmd))
        if cmd[-1] == "update":
            return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(updates_service, "_run", fake_run)
    monkeypatch.setattr(updates_service.shutil, "which", lambda name: "/usr/bin/apt" if name == "apt" else None)
    result = updates_service.apply_updates(reboot=False)
    assert result.success is True
    assert calls[0] == ["sudo", "-n", "apt-get", "update"]
    assert calls[1] == ["sudo", "-n", "DEBIAN_FRONTEND=noninteractive", "apt-get", "-y", "upgrade"]


def test_terminal_home_resolution():
    from app.routes.terminal import _terminal_home

    assert _terminal_home("exampleuser") == "/home/exampleuser"
    assert _terminal_home("ghost") == "/home/ghost"
