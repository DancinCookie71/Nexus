"""Terminal WebSocket message schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class TerminalInput(BaseModel):
    """Input sent from the client to the terminal PTY."""

    type: str = Field(..., pattern="^(input|resize)$")
    data: str | None = None
    rows: int | None = None
    cols: int | None = None
