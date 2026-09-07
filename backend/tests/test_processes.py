"""Tests for process listing and control."""
from __future__ import annotations

import os
import signal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.processes import ProcessError, kill_process, list_processes


def _proc(pid, name, username, cpu, mem, status, command=""):
    return SimpleNamespace(
        info={
            "pid": pid,
            "name": name,
            "username": username,
            "cpu_percent": cpu,
            "memory_percent": mem,
            "memory_info": SimpleNamespace(rss=1024 * 1024 * pid),
            "status": status,
            "cmdline": [command] if command else [],
        }
    )


@pytest.fixture
def fake_psutil(monkeypatch):
    def install(procs):
        fake = SimpleNamespace()
        fake.process_iter = lambda attrs: iter(procs)
        fake.cpu_percent = lambda interval=None: 12.5
        fake.virtual_memory = lambda: SimpleNamespace(percent=42.0)
        fake.getloadavg = lambda: (0.1, 0.2, 0.3)
        fake.STATUS_RUNNING = "running"
        fake.STATUS_SLEEPING = "sleeping"
        fake.NoSuchProcess = type("NoSuchProcess", (Exception,), {})
        fake.AccessDenied = type("AccessDenied", (Exception,), {})
        fake.ZombieProcess = type("ZombieProcess", (Exception,), {})
        fake.TimeoutExpired = type("TimeoutExpired", (Exception,), {})
        fake.Process = MagicMock()
        monkeypatch.setattr("app.services.processes.psutil", fake)
        return fake

    return install


def test_list_processes_sorted_and_totals(fake_psutil):
    fake_psutil(
        [
            _proc(10, "low", "nexus", 1.0, 5.0, "sleeping", "low --flag"),
            _proc(20, "high", "nexus", 9.0, 1.0, "running", "high"),
            _proc(30, "gone", "nexus", 5.0, 2.0, "running"),
        ]
    )
    result = list_processes()
    assert result["cpu_percent"] == 12.5
    assert result["memory_percent"] == 42.0
    assert result["load_average"] == [0.1, 0.2, 0.3]
    assert result["total"] == 3
    assert result["running"] == 2
    assert result["sleeping"] == 1
    assert result["processes"][0]["name"] == "high"
    assert result["processes"][0]["cpu_percent"] == 9.0
    assert result["processes"][-1]["name"] == "low"


def test_kill_rejects_protected_pids(fake_psutil):
    fake = fake_psutil([])
    with pytest.raises(ProcessError):
        kill_process(1)
    with pytest.raises(ProcessError):
        kill_process(2)
    with pytest.raises(ProcessError):
        kill_process(os.getpid())
    fake.Process.assert_not_called()


def test_kill_rejects_other_users_process(fake_psutil):
    fake = fake_psutil([])
    proc = MagicMock()
    proc.username.return_value = "somebodyelse"
    fake.Process.return_value = proc
    with pytest.raises(ProcessError):
        kill_process(1234)
    proc.send_signal.assert_not_called()


def test_kill_sends_sigterm(fake_psutil):
    fake = fake_psutil([])
    proc = MagicMock()
    proc.username.return_value = _current_username()
    fake.Process.return_value = proc
    kill_process(1234, "TERM")
    proc.send_signal.assert_called_once_with(signal.SIGTERM)
    proc.wait.assert_called_once()


def test_kill_sends_sigkill(fake_psutil):
    fake = fake_psutil([])
    proc = MagicMock()
    proc.username.return_value = _current_username()
    fake.Process.return_value = proc
    kill_process(1234, "KILL")
    proc.send_signal.assert_called_once_with(signal.SIGKILL)


def test_kill_escalates_to_sigkill_on_timeout(fake_psutil):
    fake = fake_psutil([])
    proc = MagicMock()
    proc.username.return_value = _current_username()
    proc.wait.side_effect = [fake.TimeoutExpired(), None]
    fake.Process.return_value = proc
    kill_process(1234, "TERM")
    assert proc.send_signal.call_args_list == [__import__("unittest").mock.call(signal.SIGTERM)]
    assert proc.kill.called


def test_kill_missing_process(fake_psutil):
    fake = fake_psutil([])
    fake.Process.side_effect = fake.NoSuchProcess()
    with pytest.raises(ProcessError):
        kill_process(1234)


def _current_username():
    import pwd

    return pwd.getpwuid(os.getuid()).pw_name


def test_processes_api_requires_auth(client):
    response = client.get("/api/v1/processes")
    assert response.status_code == 401


def test_processes_api_list(auth_client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.processes.list_processes",
        lambda limit=200: {
            "processes": [
                {
                    "pid": 99,
                    "name": "thing",
                    "username": "nexus",
                    "cpu_percent": 3.0,
                    "memory_percent": 1.0,
                    "memory_bytes": 2048,
                    "status": "running",
                    "command": "thing",
                }
            ],
            "total": 1,
            "running": 1,
            "sleeping": 0,
            "cpu_percent": 3.0,
            "memory_percent": 1.0,
            "load_average": [0.0, 0.0, 0.0],
        },
    )
    response = auth_client.get("/api/v1/processes")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["processes"][0]["pid"] == 99


def test_kill_api_requires_admin(auth_client):
    response = auth_client.post(
        "/api/v1/processes/99/kill",
        json={"signal": "TERM"},
    )
    assert response.status_code == 403


def test_kill_api_rejects_init(auth_client, db_session):
    from app.auth import grant_admin, get_session_by_token

    token = auth_client.headers["Authorization"].split()[1]
    session_obj = get_session_by_token(db_session, token)
    grant_admin(db_session, session_obj, sudo_username="nexus")
    response = auth_client.post(
        "/api/v1/processes/1/kill",
        json={"signal": "KILL"},
    )
    assert response.status_code == 400
    assert "cannot be stopped" in response.json()["detail"]
