"""Authentication request/response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UTCDateTime


class LoginRequest(BaseModel):
    """User login payload."""

    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class UserResponse(BaseModel):
    """Public user information."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    created_at: UTCDateTime
    updated_at: UTCDateTime


class SessionInfo(BaseModel):
    """Public session information."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_agent: Optional[str]
    ip_address: Optional[str]
    created_at: UTCDateTime
    expires_at: UTCDateTime


class LoginResponse(BaseModel):
    """Successful login response."""

    access_token: str
    token_type: str = "bearer"
    expires_at: UTCDateTime
    user: UserResponse


class CreateFirstUserRequest(BaseModel):
    """Payload for bootstrapping the first admin user."""

    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=128)


class AdminElevateRequest(BaseModel):
    """Payload for elevating to admin mode."""

    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=256)


class AdminStatusResponse(BaseModel):
    """Current admin privilege state for the session."""

    is_admin: bool
    expires_at: Optional[UTCDateTime]
    username: Optional[str]
    sudo_username: Optional[str] = None
