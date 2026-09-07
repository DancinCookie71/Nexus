"""System statistics request/response schemas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CpuInfo(BaseModel):
    """CPU statistics."""

    usage_percent: Optional[float] = Field(None, ge=0, le=100)
    cores: Optional[int] = Field(None, ge=1)
    frequency_mhz: Optional[float] = None


class MemoryInfo(BaseModel):
    """Memory (RAM) statistics."""

    total_bytes: Optional[int] = Field(None, ge=0)
    used_bytes: Optional[int] = Field(None, ge=0)
    available_bytes: Optional[int] = Field(None, ge=0)
    usage_percent: Optional[float] = Field(None, ge=0, le=100)


class DiskInfo(BaseModel):
    """Disk usage statistics."""

    total_bytes: Optional[int] = Field(None, ge=0)
    used_bytes: Optional[int] = Field(None, ge=0)
    free_bytes: Optional[int] = Field(None, ge=0)
    usage_percent: Optional[float] = Field(None, ge=0, le=100)


class SystemResponse(BaseModel):
    """Complete system snapshot."""

    cpu: CpuInfo
    memory: MemoryInfo
    disk: DiskInfo
    temperature_celsius: Optional[float]
    uptime_seconds: Optional[float]
    hostname: Optional[str]
    os: Optional[str]
    kernel: Optional[str]
    architecture: Optional[str]


class RebootResponse(BaseModel):
    """Response from a reboot request."""

    success: bool
    message: str
