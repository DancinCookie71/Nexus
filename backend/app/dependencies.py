"""FastAPI dependencies for authentication and database access."""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.auth import (
    get_session_by_token,
    get_active_admin_username,
    is_admin,
    is_unix_sudoer,
)
from app.database import get_db
from app.models import SessionToken, User
from app.services.settings import get_setting_bool

# HTTPBearer with auto_error=False lets us handle missing tokens gracefully
# and return consistent error responses.
bearer_scheme = HTTPBearer(auto_error=False)


def _extract_token_from_request(request: Request) -> Optional[str]:
    """Extract bearer token from Authorization header or secure cookie."""
    # Prefer Authorization header (used by mobile/API clients).
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()

    # Fallback to HTTP-only cookie (used by web client).
    cookie_token = request.cookies.get("nexus_session")
    if cookie_token:
        return cookie_token

    return None


def get_current_session(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> SessionToken:
    """Return the current valid session or raise 401."""
    token: Optional[str] = None
    if credentials is not None:
        token = credentials.credentials
    else:
        token = _extract_token_from_request(request)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    session_obj = get_session_by_token(db, token)
    if session_obj is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return session_obj


def get_current_user(
    session: SessionToken = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> User:
    """Return the user associated with the current session."""
    user = db.query(User).filter(User.id == session.user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(
    session: SessionToken = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> SessionToken:
    """Ensure the current session has active admin privileges.

    A UNIX-backed panel user in an admin group (sudo/wheel) is treated as
    admin automatically, Cockpit-style; otherwise elevation is required.
    """
    if is_admin(db, session):
        return session
    user = db.query(User).filter(User.id == session.user_id).first()
    if user is not None and user.auth_source == "unix" and is_unix_sudoer(user.username):
        return session
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin privileges required. Enable Admin mode from the top bar.",
    )


def require_admin_if_files_writes_locked(
    session: SessionToken = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> SessionToken:
    """Require admin privileges when file write locking is enabled in settings."""
    if get_setting_bool(db, "require_admin_for_files_writes", default=False):
        return require_admin(session, db)
    return session


def get_optional_admin_user(
    session: SessionToken = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> Optional[str]:
    """Return the effective file-operator username for the session.

    The active admin sudo username wins; otherwise a UNIX-backed panel user
    operates on files as their own account.
    """
    admin_user = get_active_admin_username(db, session)
    if admin_user:
        return admin_user
    user = db.query(User).filter(User.id == session.user_id).first()
    if user is not None and user.auth_source == "unix":
        return user.username
    return None


class RateLimiter:
    """Simple in-memory rate limiter for login attempts."""

    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, list[float]] = {}

    def is_allowed(self, key: str) -> bool:
        """Check whether a key is currently allowed to attempt login."""
        import time

        now = time.time()
        window_start = now - self.window_seconds
        attempts = [t for t in self._attempts.get(key, []) if t > window_start]
        self._attempts[key] = attempts
        return len(attempts) < self.max_attempts

    def record_attempt(self, key: str) -> None:
        """Record a failed login attempt for a key."""
        import time

        self._attempts.setdefault(key, []).append(time.time())

    def clear_attempts(self, key: str) -> None:
        """Clear recorded attempts for a key after a successful login."""
        self._attempts.pop(key, None)

    def reset(self) -> None:
        """Reset all recorded attempts. Useful for tests."""
        self._attempts.clear()


login_rate_limiter = RateLimiter(max_attempts=5, window_seconds=300)

# Rate limiter for admin elevation attempts (separate from login).
admin_elevation_limiter = RateLimiter(max_attempts=5, window_seconds=300)
