"""Log response schemas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class LogEntry(BaseModel):
    """A single journal log entry."""

    timestamp: Optional[str]
    priority: int
    priority_name: str
    unit: str
    identifier: str
    message: str


class LogsResponse(BaseModel):
    """Response for log queries."""

    unit: str
    entries: list[LogEntry]
    total: int
    limit: int
    since: Optional[str] = None
    until: Optional[str] = None
    priority: Optional[int] = None
