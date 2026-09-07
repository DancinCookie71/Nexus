"""Interactive terminal WebSocket endpoint using a server-side PTY."""
from __future__ import annotations

import asyncio
import fcntl
import json
import os
import pty
import signal
import struct
import termios
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.auth import get_session_by_token, get_active_admin_username, is_admin
from app.config import settings
from app.database import get_db
from app.models import User
from app.services.settings import get_setting_bool

router = APIRouter(prefix="/terminal", tags=["terminal"])

# Track active terminal sessions for cleanup.
active_terminals: dict[str, dict] = {}


def _resolve_terminal_user(db: Session, session) -> Optional[str]:
    """Return the UNIX account the terminal should run as.

    The active admin sudo username wins; otherwise a UNIX-backed panel user
    gets a shell as their own account. Local-only panel users fall back to nexus.
    """
    admin_user = get_active_admin_username(db, session)
    if admin_user:
        return admin_user
    session_user = db.query(User).filter(User.id == session.user_id).first()
    if session_user is not None and session_user.auth_source == "unix":
        return session_user.username
    return None


def _extract_token_from_ws(websocket: WebSocket) -> Optional[str]:
    """Extract bearer token, session cookie, or query token from a WebSocket handshake."""
    auth_header = websocket.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    cookie_token = websocket.cookies.get("nexus_session")
    if cookie_token:
        return cookie_token
    query_token = websocket.query_params.get("token")
    if query_token:
        return query_token
    return None


def _set_terminal_size(fd: int, rows: Optional[int], cols: Optional[int]) -> None:
    """Resize the PTY."""
    if rows is None or cols is None:
        return
    try:
        size = struct.pack("HHHH", int(rows), int(cols), 0, 0)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, size)
    except (OSError, ValueError):
        pass


def _terminal_home(username: str) -> str:
    try:
        import pwd

        return pwd.getpwnam(username).pw_dir or f"/home/{username}"
    except KeyError:
        return f"/home/{username}"


@router.websocket("/ws")
async def terminal_ws(websocket: WebSocket, db: Session = Depends(get_db)):
    """Authenticated interactive PTY terminal over WebSocket.

    Authentication uses the same bearer token or HTTP-only session cookie
    as the REST API, so the token is never exposed to frontend JavaScript.
    """
    if not settings.terminal_enabled:
        await websocket.close(code=1008, reason="Terminal is disabled")
        return

    token = _extract_token_from_ws(websocket)
    if not token:
        await websocket.close(code=1008, reason="Authentication required")
        return

    session = get_session_by_token(db, token)
    if session is None:
        await websocket.close(code=1008, reason="Invalid or expired session")
        return

    # If configured, require admin mode for terminal access.
    if get_setting_bool(db, "require_admin_for_terminal", default=False):
        if not is_admin(db, session):
            await websocket.close(code=1008, reason="Admin privileges required")
            return

    # Enforce per-user session limit.
    user_session_count = sum(
        1 for t in active_terminals.values() if t.get("user_id") == session.user_id
    )
    if user_session_count >= settings.terminal_max_sessions_per_user:
        await websocket.close(code=1008, reason="Maximum terminal sessions reached")
        return

    await websocket.accept()

    try:
        pid, master_fd = pty.fork()
    except OSError as exc:
        await websocket.close(code=1011, reason="Unable to allocate terminal")
        return

    terminal_user = _resolve_terminal_user(db, session)

    if pid == 0:
        # Child process: close inherited file descriptors so the shell does not
        # hold on to the server's listening sockets or other resources.
        for fd in range(3, 256):
            try:
                os.close(fd)
            except OSError:
                pass
        # Set a standard TERM so tools like clear, nano, and top work correctly.
        os.environ["TERM"] = "xterm-256color"
        os.environ["SHELL"] = settings.terminal_shell
        # Drop panel configuration variables so they never reach the user's
        # shell environment (sudo -E preserves the environment as-is).
        for key in [k for k in os.environ if k.startswith("NEXUS_")]:
            del os.environ[key]
        if terminal_user:
            # Run the terminal as the authenticated user, starting in
            # their home directory.
            home = _terminal_home(terminal_user)
            os.environ["HOME"] = home
            try:
                os.chdir(home)
            except OSError:
                os.chdir("/")
            try:
                os.execv("/usr/bin/sudo", ["sudo", "-n", "-u", terminal_user, "-E", "-H", "/bin/bash", "-l"])
            except OSError:
                pass
        # Replace with the configured shell as the unprivileged nexus user.
        try:
            os.execv(settings.terminal_shell, [settings.terminal_shell, "-l"])
        except OSError:
            pass
        os._exit(1)

    # Parent process.
    terminal_id = str(uuid.uuid4())
    active_terminals[terminal_id] = {
        "user_id": session.user_id,
        "pid": pid,
        "master_fd": master_fd,
    }

    loop = asyncio.get_event_loop()

    async def read_output() -> None:
        """Read PTY output and forward to the WebSocket client."""
        try:
            while True:
                data = await loop.run_in_executor(None, os.read, master_fd, 4096)
                if not data:
                    break
                await websocket.send_text(data.decode("utf-8", errors="replace"))
        except asyncio.CancelledError:
            pass
        except OSError:
            pass

    read_task = asyncio.create_task(read_output())

    async def cleanup() -> None:
        """Terminate the shell and close the PTY."""
        active_terminals.pop(terminal_id, None)
        read_task.cancel()

        def _terminate() -> None:
            """Run blocking process cleanup in a worker thread."""
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                return
            try:
                # Give the shell a moment to shut down cleanly.
                import time
                for _ in range(20):
                    time.sleep(0.05)
                    try:
                        if os.waitpid(pid, os.WNOHANG)[0] != 0:
                            return
                    except ChildProcessError:
                        return
                # Force kill if still running.
                os.kill(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
            except (ProcessLookupError, ChildProcessError):
                pass

        await loop.run_in_executor(None, _terminate)
        try:
            os.close(master_fd)
        except OSError:
            pass

    try:
        while True:
            message = await websocket.receive_text()
            try:
                msg = json.loads(message)
                msg_type = msg.get("type")
                if msg_type == "input" and isinstance(msg.get("data"), str):
                    data = msg["data"].encode("utf-8")
                    await loop.run_in_executor(None, os.write, master_fd, data)
                elif msg_type == "resize":
                    _set_terminal_size(master_fd, msg.get("rows"), msg.get("cols"))
            except (json.JSONDecodeError, KeyError, TypeError, OSError):
                continue
    except WebSocketDisconnect:
        pass
    finally:
        await cleanup()
