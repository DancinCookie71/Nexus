"""Authentication helpers: password hashing and token management."""
from __future__ import annotations

import hashlib
import pwd
import re
import secrets
import subprocess
from datetime import datetime, timedelta, timezone
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AdminSession, SessionToken, User

# Argon2id with sensible defaults.
ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16)

TOKEN_BYTES = 32


def hash_password(password: str) -> str:
    """Hash a plaintext password with Argon2id."""
    return ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against an Argon2id hash."""
    try:
        ph.verify(password_hash, password)
        return True
    except (VerifyMismatchError, InvalidHashError):
        return False


def _hash_token(token: str) -> str:
    """Hash a bearer token for storage using SHA-256."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_token() -> str:
    """Generate a cryptographically secure bearer token."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def create_user(db: Session, username: str, password: str) -> User:
    """Create a new user with a hashed password."""
    user = User(username=username, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate a user by username and password."""
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


_MIN_REAL_USER_UID = 1000
_SYSTEM_SHELL_BASENAMES = {"nologin", "false"}
RESERVED_USERNAMES = {"nexus", "admin", "root"}
UNLIMITED_ADMIN_DAYS = 36500


def is_reserved_username(username: str) -> bool:
    """Return True if the username may never be used to log in."""
    return username.strip().lower() in RESERVED_USERNAMES


_ADMIN_GROUPS = ("sudo", "wheel")


def is_unix_sudoer(username: str) -> bool:
    """Return True if the local UNIX account is a member of an admin group."""
    if not _valid_linux_username(username):
        return False
    try:
        entry = pwd.getpwnam(username)
    except KeyError:
        return False
    import grp

    for group_name in _ADMIN_GROUPS:
        try:
            group = grp.getgrnam(group_name)
        except KeyError:
            continue
        if username in group.gr_mem or entry.pw_gid == group.gr_gid:
            return True
    return False


def is_real_unix_user(username: str) -> bool:
    """Return True if username is a human (non-system) local UNIX account.

    Real accounts are UID >= 1000 with a usable login shell; service and
    program-generated accounts (www-data, nexus, etc.) are excluded.
    """
    if not _valid_linux_username(username):
        return False
    try:
        entry = pwd.getpwnam(username)
    except KeyError:
        return False
    shell = entry.pw_shell.rsplit("/", 1)[-1].lower() if entry.pw_shell else ""
    return entry.pw_uid >= _MIN_REAL_USER_UID and shell not in _SYSTEM_SHELL_BASENAMES


def get_or_create_unix_user(db: Session, username: str) -> User:
    """Return the panel user for a UNIX account, creating it on first login."""
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        user = User(username=username, password_hash="", auth_source="unix")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def create_session(
    db: Session,
    user_id: str,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> tuple[SessionToken, str]:
    """Create a new session and return the model plus the plaintext token."""
    plaintext = generate_token()
    token_hash = _hash_token(plaintext)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.session_lifetime_minutes)
    session_obj = SessionToken(
        user_id=user_id,
        token_hash=token_hash,
        user_agent=user_agent,
        ip_address=ip_address,
        expires_at=expires_at,
    )
    db.add(session_obj)
    db.commit()
    db.refresh(session_obj)
    return session_obj, plaintext


def get_session_by_token(db: Session, token: str) -> Optional[SessionToken]:
    """Look up a non-expired, non-revoked session by plaintext token."""
    token_hash = _hash_token(token)
    session_obj = (
        db.query(SessionToken)
        .filter(
            SessionToken.token_hash == token_hash,
            SessionToken.revoked_at.is_(None),
            SessionToken.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )
    return session_obj


def revoke_session(db: Session, session_obj: SessionToken) -> None:
    """Revoke a session immediately."""
    session_obj.revoked_at = datetime.now(timezone.utc)
    db.commit()


def revoke_session_by_id(db: Session, user_id: str, session_id: str) -> bool:
    """Revoke one of the user's own sessions by ID. Returns True if found."""
    session_obj = (
        db.query(SessionToken)
        .filter(
            SessionToken.id == session_id,
            SessionToken.user_id == user_id,
            SessionToken.revoked_at.is_(None),
        )
        .first()
    )
    if session_obj is None:
        return False
    revoke_session(db, session_obj)
    return True


def list_active_sessions(db: Session, user_id: str) -> list[SessionToken]:
    """Return active (non-revoked, non-expired) sessions for a user."""
    return (
        db.query(SessionToken)
        .filter(
            SessionToken.user_id == user_id,
            SessionToken.revoked_at.is_(None),
            SessionToken.expires_at > datetime.now(timezone.utc),
        )
        .order_by(SessionToken.created_at.desc())
        .all()
    )


def cleanup_expired_sessions(db: Session) -> int:
    """Delete expired or revoked sessions. Returns the number deleted."""
    now = datetime.now(timezone.utc)
    result = (
        db.query(SessionToken)
        .filter(
            (SessionToken.expires_at <= now) | (SessionToken.revoked_at.isnot(None))
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    return result


def _valid_linux_username(username: str) -> bool:
    """Return True if username looks like a local Linux user name."""
    return bool(re.match(r"^[a-z_][a-z0-9_-]{0,31}$", username))


def verify_system_password(username: str, password: str) -> bool:
    """Verify a local Linux user's password using su(1).

    This intentionally does not grant any privileges; it only proves the
    user knows the password for an authorized system account. su(1) is
    setuid root, so it can verify any local password from the unprivileged
    nexus service account.
    """
    if not _valid_linux_username(username):
        return False
    if not password or len(password) > 256:
        return False
    try:
        proc = subprocess.run(
            ["su", "-s", "/bin/sh", username, "-c", "echo nexus-auth-ok"],
            input=password + "\n",
            capture_output=True,
            text=True,
            timeout=10,
        )
        return proc.returncode == 0 and "nexus-auth-ok" in proc.stdout
    except Exception:
        return False


def _configured_admin_lifetime_minutes(db: Session) -> int:
    """Return the admin elevation lifetime from settings, falling back to config."""
    from app.services.settings import get_setting_int

    return get_setting_int(
        db, "admin_session_lifetime_minutes", default=settings.admin_session_lifetime_minutes
    )


def grant_admin(
    db: Session,
    session_obj: SessionToken,
    duration_minutes: Optional[int] = None,
    ip_address: Optional[str] = None,
    sudo_username: Optional[str] = None,
) -> AdminSession:
    """Create a temporary admin privilege elevation for a web session.

    A duration of 0 or less (the default when the setting is 0) never expires.
    """
    if duration_minutes is None:
        duration = _configured_admin_lifetime_minutes(db)
    else:
        duration = duration_minutes
    now = datetime.now(timezone.utc)
    if duration > 0:
        expires_at = now + timedelta(minutes=duration)
    else:
        expires_at = now + timedelta(days=UNLIMITED_ADMIN_DAYS)
    admin_session = AdminSession(
        session_id=session_obj.id,
        user_id=session_obj.user_id,
        sudo_username=sudo_username,
        granted_at=now,
        expires_at=expires_at,
        ip_address=ip_address,
    )
    db.add(admin_session)
    db.commit()
    db.refresh(admin_session)
    return admin_session


def get_active_admin_session(
    db: Session, session_obj: SessionToken
) -> Optional[AdminSession]:
    """Return the current active admin session for a web session, if any."""
    now = datetime.now(timezone.utc)
    return (
        db.query(AdminSession)
        .filter(
            AdminSession.session_id == session_obj.id,
            AdminSession.user_id == session_obj.user_id,
            AdminSession.revoked_at.is_(None),
            AdminSession.expires_at > now,
        )
        .order_by(AdminSession.granted_at.desc())
        .first()
    )


def is_admin(db: Session, session_obj: SessionToken) -> bool:
    """Return True if the session currently has active admin privileges."""
    return get_active_admin_session(db, session_obj) is not None


def get_active_admin_username(
    db: Session, session_obj: SessionToken
) -> Optional[str]:
    """Return the authenticated sudo username for the active admin session."""
    active = get_active_admin_session(db, session_obj)
    return active.sudo_username if active else None


def revoke_admin(db: Session, session_obj: SessionToken) -> bool:
    """Revoke all active admin grants for a session. Returns True if any existed."""
    now = datetime.now(timezone.utc)
    grants = (
        db.query(AdminSession)
        .filter(
            AdminSession.session_id == session_obj.id,
            AdminSession.user_id == session_obj.user_id,
            AdminSession.revoked_at.is_(None),
            AdminSession.expires_at > now,
        )
        .all()
    )
    if not grants:
        return False
    for grant in grants:
        grant.revoked_at = now
    db.commit()
    return True


def cleanup_expired_admin_sessions(db: Session) -> int:
    """Delete expired admin sessions. Returns the number deleted."""
    now = datetime.now(timezone.utc)
    result = (
        db.query(AdminSession)
        .filter(
            (AdminSession.expires_at <= now) | (AdminSession.revoked_at.isnot(None))
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    return result
