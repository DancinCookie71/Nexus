"""System statistics collection service."""
from __future__ import annotations

import platform
from datetime import datetime, timezone
from typing import Optional

import psutil

from app.schemas.system import CpuInfo, DiskInfo, MemoryInfo, SystemResponse


def _get_cpu_frequency_mhz() -> Optional[float]:
    """Return current CPU frequency in MHz if available."""
    try:
        freq = psutil.cpu_freq()
        if freq is None:
            return None
        return round(freq.current, 1)
    except Exception:
        return None


def _get_temperature_celsius() -> Optional[float]:
    """Return average CPU temperature if available."""
    try:
        temps = psutil.sensors_temperatures()
        if not temps:
            return None
        # Prefer known thermal zones; fall back to first available sensor.
        candidates = []
        for name, entries in temps.items():
            for entry in entries:
                if entry.current is not None:
                    candidates.append(entry.current)
        if not candidates:
            return None
        return round(sum(candidates) / len(candidates), 1)
    except Exception:
        return None


def _get_uptime_seconds() -> Optional[float]:
    """Return system uptime in seconds."""
    try:
        import time

        return round(time.time() - psutil.boot_time(), 0)
    except Exception:
        return None


def _get_disk_usage() -> Optional[psutil._psplatform.DiskUsage]:
    """Return disk usage for the root filesystem."""
    try:
        return psutil.disk_usage("/")
    except Exception:
        return None


def get_system_snapshot() -> SystemResponse:
    """Collect a full system statistics snapshot."""
    cpu_usage: Optional[float] = None
    try:
        cpu_usage = round(psutil.cpu_percent(interval=None), 1)
    except Exception:
        pass

    cpu_cores: Optional[int] = None
    try:
        cpu_cores = psutil.cpu_count(logical=True)
    except Exception:
        pass

    memory = MemoryInfo()
    try:
        mem = psutil.virtual_memory()
        memory = MemoryInfo(
            total_bytes=mem.total,
            used_bytes=mem.used,
            available_bytes=mem.available,
            usage_percent=round(mem.percent, 1),
        )
    except Exception:
        pass

    disk = DiskInfo()
    du = _get_disk_usage()
    if du is not None:
        disk = DiskInfo(
            total_bytes=du.total,
            used_bytes=du.used,
            free_bytes=du.free,
            usage_percent=round(du.percent, 1),
        )

    os_name = platform.system() or None
    os_version = platform.release() or None
    os_label = f"{os_name} {os_version}".strip() if os_name or os_version else None

    return SystemResponse(
        cpu=CpuInfo(
            usage_percent=cpu_usage,
            cores=cpu_cores,
            frequency_mhz=_get_cpu_frequency_mhz(),
        ),
        memory=memory,
        disk=disk,
        temperature_celsius=_get_temperature_celsius(),
        uptime_seconds=_get_uptime_seconds(),
        hostname=platform.node() or None,
        os=os_label,
        kernel=platform.release() or None,
        architecture=platform.machine() or None,
    )
