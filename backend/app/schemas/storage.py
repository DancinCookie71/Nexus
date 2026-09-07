"""Storage/drive management schemas."""
from __future__ import annotations

from pydantic import BaseModel


class SmartAttribute(BaseModel):
    id: int
    name: str
    flag: str
    value: int | None
    worst: int | None
    threshold: int | None
    type: str
    updated: str
    when_failed: str
    raw_value: str


class DriveSummary(BaseModel):
    device: str
    model: str
    serial: str
    size_human: str
    is_ssd: bool
    smart_supported: bool
    smart_enabled: bool
    smart_status: str
    temperature_c: int | None
    power_on_hours: int | None
    status: str


class DriveDetail(BaseModel):
    device: str
    model: str
    serial: str
    firmware: str
    size_bytes: int
    size_human: str
    rotation_rate: int | None
    is_ssd: bool
    smart_supported: bool
    smart_enabled: bool
    smart_status: str
    temperature_c: int | None
    power_on_hours: int | None
    status: str
    attributes: list[SmartAttribute]
    messages: list[str]


class DriveListResponse(BaseModel):
    drives: list[DriveSummary]
    total: int
