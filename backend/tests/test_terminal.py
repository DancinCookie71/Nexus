"""Tests for terminal WebSocket endpoint."""
from __future__ import annotations

import pytest
from starlette.websockets import WebSocketDisconnect

from app.auth import create_user


@pytest.fixture
def terminal_user(db_session):
    return create_user(db_session, "terminaladmin", "StrongPassword123!")


@pytest.fixture
def terminal_token(db_session, terminal_user):
    from app.auth import create_session
    _, token = create_session(db_session, terminal_user.id)
    return token


def test_terminal_unauthenticated(client):
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/terminal/ws") as ws:
            ws.receive()
    assert exc_info.value.code == 1008


def test_terminal_authenticated(client, terminal_token):
    # Successful entry into the context manager means the connection was accepted.
    with client.websocket_connect(f"/api/v1/terminal/ws?token={terminal_token}") as ws:
        # Send a benign command and immediately exit to keep the test fast.
        ws.send_json({"type": "input", "data": "echo ok\n"})
        ws.send_json({"type": "input", "data": "exit\n"})
        # Drain a few messages so the command is processed before close.
        for _ in range(5):
            try:
                ws.receive_text(timeout=0.5)
            except Exception:
                break


def test_terminal_disabled(client, terminal_token, monkeypatch):
    monkeypatch.setenv("TERMINAL", "false")
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/api/v1/terminal/ws?token={terminal_token}") as ws:
            ws.receive()
    assert exc_info.value.code == 1008
