"""SQLAlchemy models for Nexus API."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base


def utc_now() -> datetime:
    """Return timezone-aware UTC now."""
    return datetime.now(timezone.utc)


class User(Base):
    """A local administrator account."""

    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    auth_source = Column(String, nullable=False, default="local")
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class SessionToken(Base):
    """An authenticated session/token."""

    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    token_hash = Column(String, unique=True, nullable=False, index=True)
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)


class ServiceActionLog(Base):
    """Audit log for administrative service actions."""

    __tablename__ = "service_action_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    service_name = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)  # start, stop, restart, status
    status = Column(String, nullable=False)  # success, error
    detail = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class AdminSession(Base):
    """Temporary privilege elevation session for the web UI."""

    __tablename__ = "admin_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    sudo_username = Column(String, nullable=True)
    granted_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    ip_address = Column(String, nullable=True)


class Setting(Base):
    """Persistent key/value settings for Nexus."""

    __tablename__ = "settings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(String, nullable=False)
    category = Column(String, nullable=False, default="general")
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
