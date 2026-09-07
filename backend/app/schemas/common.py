"""Common response schemas."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, PlainSerializer


def _serialize_utc_datetime(value: datetime) -> str:
    """Serialize a datetime as ISO 8601 with a trailing Z (UTC).

    SQLite returns naive datetimes; treat them as UTC before serializing.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


UTCDateTime = Annotated[datetime, PlainSerializer(_serialize_utc_datetime, when_used="json")]


class ErrorResponse(BaseModel):
    """Standard error response body."""

    detail: str


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
