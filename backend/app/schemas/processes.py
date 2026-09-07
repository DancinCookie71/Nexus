"""Process listing request/response schemas."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ProcessInfo(BaseModel):
    """A single system process."""

    pid: int
    name: str
    username: str
    cpu_percent: float
    memory_percent: float
    memory_bytes: int
    status: str
    command: str


class ProcessListResponse(BaseModel):
    """Snapshot of system processes with totals."""

    processes: list[ProcessInfo]
    total: int
    running: int
    sleeping: int
    cpu_percent: float
    memory_percent: float
    load_average: list[float]


class ProcessKillRequest(BaseModel):
    """Request to signal a process."""

    signal: Literal["TERM", "KILL"] = "TERM"
