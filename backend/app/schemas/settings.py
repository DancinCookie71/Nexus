"""Settings request/response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UTCDateTime


class SettingValue(BaseModel):
    """A single setting value."""

    model_config = ConfigDict(from_attributes=True)

    key: str
    value: str
    category: str
    updated_at: UTCDateTime


class SettingUpdateRequest(BaseModel):
    """Payload to update a setting."""

    value: str = Field(..., min_length=0, max_length=4096)


class SettingsCategoryResponse(BaseModel):
    """Settings grouped by category."""

    categories: dict[str, dict[str, str]]


class SettingCreateRequest(BaseModel):
    """Payload to create or overwrite a setting."""

    key: str = Field(..., min_length=1, max_length=128)
    value: str = Field(..., min_length=0, max_length=4096)
    category: str = Field(default="general", max_length=64)
