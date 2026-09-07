"""UNIX account management request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class UnixUserInfo(BaseModel):
    """A human local UNIX account."""

    username: str
    full_name: str
    home: str
    shell: str
    uid: int
    is_admin: bool


class UnixUserCreateRequest(BaseModel):
    """Payload for creating a local UNIX account."""

    username: str = Field(..., pattern=r"^[a-z_][a-z0-9_-]{0,31}$")
    full_name: str = Field("", max_length=64)
    password: str = Field(..., min_length=8, max_length=128)
    shell: str = Field("/bin/bash", max_length=64)


class UnixUserPasswordRequest(BaseModel):
    """Payload for setting a user's password."""

    password: str = Field(..., min_length=8, max_length=128)


class UnixUserAdminRequest(BaseModel):
    """Payload for toggling sudo-group membership."""

    admin: bool
