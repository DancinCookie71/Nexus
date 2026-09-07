"""Health monitoring request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel


class CpuHealth(BaseModel):
    percent: float
    per_cpu: list[float]
    load_1: float
    load_5: float
    load_15: float
    frequency_mhz: float | None
    temperature_c: float | None


class MemoryHealth(BaseModel):
    total_bytes: int
    used_bytes: int
    available_bytes: int
    percent: float
    swap_total_bytes: int
    swap_used_bytes: int
    swap_percent: float


class DiskHealth(BaseModel):
    device: str
    mountpoint: str
    fstype: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    percent: float
    read_bytes_per_sec: float
    write_bytes_per_sec: float
    iops: float
    temperature_c: float | None
    smart_status: str
    smart_failing: bool
    errors: list[str]


class NetworkInterfaceHealth(BaseModel):
    name: str
    is_up: bool
    speed_mbps: float | None
    mtu: int
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    errin: int
    errout: int
    dropin: int
    dropout: int
    bytes_sent_per_sec: float
    bytes_recv_per_sec: float


class NetworkHealth(BaseModel):
    total_bytes_sent_per_sec: float
    total_bytes_recv_per_sec: float
    latency_ms: float | None
    interfaces: list[NetworkInterfaceHealth]


class GpuHealth(BaseModel):
    name: str
    utilization_percent: float | None
    temperature_c: float | None
    memory_total_bytes: int | None
    memory_used_bytes: int | None


class SensorReading(BaseModel):
    label: str
    value: float | None
    unit: str


class DriveHealth(BaseModel):
    device: str
    status: str
    smart_status: str
    temperature_c: float | None


class HealthResponse(BaseModel):
    timestamp: float
    overall: str
    cpu: CpuHealth
    memory: MemoryHealth
    disks: list[DiskHealth]
    drives: list[DriveHealth]
    network: NetworkHealth
    gpus: list[GpuHealth]
    uptime_seconds: float
    failed_services: list[str]
    filesystem_errors: list[str]
    update_count: int
    sensors: list[SensorReading]
