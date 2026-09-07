"""System health monitoring collection helpers."""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from typing import Optional

import psutil


@dataclass
class CpuSnapshot:
    percent: float = 0.0
    per_cpu: list[float] = field(default_factory=list)
    load_1: float = 0.0
    load_5: float = 0.0
    load_15: float = 0.0
    frequency_mhz: Optional[float] = None
    temperature_c: Optional[float] = None


@dataclass
class MemorySnapshot:
    total_bytes: int = 0
    used_bytes: int = 0
    available_bytes: int = 0
    percent: float = 0.0
    swap_total_bytes: int = 0
    swap_used_bytes: int = 0
    swap_percent: float = 0.0


@dataclass
class DiskSnapshot:
    device: str = ""
    mountpoint: str = ""
    fstype: str = ""
    total_bytes: int = 0
    used_bytes: int = 0
    free_bytes: int = 0
    percent: float = 0.0
    read_bytes: int = 0
    write_bytes: int = 0
    read_count: int = 0
    write_count: int = 0
    read_bytes_per_sec: float = 0.0
    write_bytes_per_sec: float = 0.0
    iops: float = 0.0
    temperature_c: Optional[float] = None
    smart_status: str = "unknown"
    smart_failing: bool = False
    errors: list[str] = field(default_factory=list)


@dataclass
class NetworkInterfaceSnapshot:
    name: str = ""
    is_up: bool = False
    speed_mbps: Optional[float] = None
    mtu: int = 0
    bytes_sent: int = 0
    bytes_recv: int = 0
    packets_sent: int = 0
    packets_recv: int = 0
    errin: int = 0
    errout: int = 0
    dropin: int = 0
    dropout: int = 0
    bytes_sent_per_sec: float = 0.0
    bytes_recv_per_sec: float = 0.0


@dataclass
class NetworkSnapshot:
    interfaces: list[NetworkInterfaceSnapshot] = field(default_factory=list)
    total_bytes_sent_per_sec: float = 0.0
    total_bytes_recv_per_sec: float = 0.0
    latency_ms: Optional[float] = None


@dataclass
class GpuSnapshot:
    name: str = ""
    utilization_percent: Optional[float] = None
    temperature_c: Optional[float] = None
    memory_total_bytes: Optional[int] = None
    memory_used_bytes: Optional[int] = None


@dataclass
class SensorReading:
    label: str = ""
    value: Optional[float] = None
    unit: str = ""


@dataclass
class DriveHealthSummary:
    device: str = ""
    status: str = "unknown"
    smart_status: str = "unknown"
    temperature_c: Optional[float] = None


@dataclass
class HealthSnapshot:
    timestamp: float = field(default_factory=time.time)
    overall: str = "healthy"
    cpu: CpuSnapshot = field(default_factory=CpuSnapshot)
    memory: MemorySnapshot = field(default_factory=MemorySnapshot)
    disks: list[DiskSnapshot] = field(default_factory=list)
    drives: list[DriveHealthSummary] = field(default_factory=list)
    network: NetworkSnapshot = field(default_factory=NetworkSnapshot)
    gpus: list[GpuSnapshot] = field(default_factory=list)
    uptime_seconds: float = 0.0
    failed_services: list[str] = field(default_factory=list)
    filesystem_errors: list[str] = field(default_factory=list)
    update_count: int = 0
    sensors: list[SensorReading] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)


def _run(cmd: list[str], timeout: int = 15) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as exc:
        return -1, "", str(exc)


def _get_cpu_temperature() -> Optional[float]:
    try:
        temps = psutil.sensors_temperatures()
        for name, entries in temps.items():
            for entry in entries:
                if entry.current is not None:
                    return float(entry.current)
    except Exception:
        pass
    return None


def _get_load_average() -> tuple[float, float, float]:
    try:
        return os.getloadavg()
    except Exception:
        return 0.0, 0.0, 0.0


def get_cpu_snapshot() -> CpuSnapshot:
    try:
        percent = psutil.cpu_percent(interval=0.5)
        per_cpu = psutil.cpu_percent(interval=0.0, percpu=True)
        freq = psutil.cpu_freq()
        load_1, load_5, load_15 = _get_load_average()
        return CpuSnapshot(
            percent=percent,
            per_cpu=per_cpu if isinstance(per_cpu, list) else [],
            load_1=load_1,
            load_5=load_5,
            load_15=load_15,
            frequency_mhz=freq.current if freq else None,
            temperature_c=_get_cpu_temperature(),
        )
    except Exception as exc:
        return CpuSnapshot(percent=0.0)


def get_memory_snapshot() -> MemorySnapshot:
    try:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return MemorySnapshot(
            total_bytes=mem.total,
            used_bytes=mem.used,
            available_bytes=mem.available,
            percent=mem.percent,
            swap_total_bytes=swap.total,
            swap_used_bytes=swap.used,
            swap_percent=swap.percent,
        )
    except Exception as exc:
        return MemorySnapshot()


def _smart_available() -> bool:
    return shutil.which("smartctl") is not None


def _get_disk_temperature(device: str) -> Optional[float]:
    if not shutil.which("smartctl"):
        return None
    rc, out, _ = _run(["sudo", "-n", "smartctl", "-A", device])
    if rc != 0:
        return None
    for line in out.splitlines():
        if "Temperature_Celsius" in line or "Airflow_Temperature_Cel" in line:
            parts = line.split()
            for part in parts:
                try:
                    return float(part)
                except ValueError:
                    continue
    return None


def _get_smart_health(device: str) -> tuple[str, bool]:
    if not shutil.which("smartctl"):
        return "unknown", False
    rc, out, _ = _run(["sudo", "-n", "smartctl", "-H", device])
    if rc != 0:
        return "unknown", False
    lower = out.lower()
    if "passed" in lower or "ok" in lower:
        return "passed", False
    if "failed" in lower:
        return "failed", True
    return "unknown", False


def _get_filesystem_errors() -> list[str]:
    errors: list[str] = []
    if shutil.which("journalctl"):
        rc, out, _ = _run([
            "journalctl",
            "--priority=err",
            "--since=-1 hour",
            "--no-pager",
            "--quiet",
            "-k",
        ], timeout=10)
        if rc == 0 and out:
            for line in out.splitlines()[-20:]:
                line = line.strip()
                if line and ("ext4" in line.lower() or "xfs" in line.lower() or "filesystem" in line.lower() or "i/o error" in line.lower()):
                    errors.append(line)
    return errors[:10]


def _get_disk_io_devices() -> dict[str, psutil._psplatform.DiskIO]:
    try:
        return psutil.disk_io_counters(perdisk=True) or {}
    except Exception:
        return {}


def get_disk_snapshots(
    previous_io: dict[str, psutil._psplatform.DiskIO] | None = None,
    elapsed_seconds: float = 1.0,
    include_smart: bool = True,
) -> tuple[list[DiskSnapshot], dict[str, psutil._psplatform.DiskIO]]:
    disks: list[DiskSnapshot] = []
    current_io = _get_disk_io_devices()
    fs_errors = _get_filesystem_errors()

    try:
        partitions = psutil.disk_partitions(all=False)
    except Exception:
        partitions = []

    for part in partitions:
        if part.fstype in ("squashfs", "tmpfs", "devtmpfs", "overlay"):
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except Exception:
            continue

        device_name = os.path.basename(part.device)
        io = current_io.get(device_name)
        prev_io = previous_io.get(device_name) if previous_io else None
        read_bps = 0.0
        write_bps = 0.0
        iops = 0.0
        read_bytes = io.read_bytes if io else 0
        write_bytes = io.write_bytes if io else 0
        read_count = io.read_count if io else 0
        write_count = io.write_count if io else 0
        if io and prev_io and elapsed_seconds > 0:
            read_bps = max(0.0, (io.read_bytes - prev_io.read_bytes) / elapsed_seconds)
            write_bps = max(0.0, (io.write_bytes - prev_io.write_bytes) / elapsed_seconds)
            iops = max(0.0, (io.read_count + io.write_count - prev_io.read_count - prev_io.write_count) / elapsed_seconds)

        if include_smart:
            smart_status, smart_failing = _get_smart_health(part.device)
            temp = _get_disk_temperature(part.device)
        else:
            smart_status, smart_failing = "unknown", False
            temp = None

        disk_errors = [e for e in fs_errors if device_name in e or part.mountpoint in e]

        disks.append(DiskSnapshot(
            device=part.device,
            mountpoint=part.mountpoint,
            fstype=part.fstype,
            total_bytes=usage.total,
            used_bytes=usage.used,
            free_bytes=usage.free,
            percent=usage.percent,
            read_bytes=read_bytes,
            write_bytes=write_bytes,
            read_count=read_count,
            write_count=write_count,
            read_bytes_per_sec=read_bps,
            write_bytes_per_sec=write_bps,
            iops=iops,
            temperature_c=temp,
            smart_status=smart_status,
            smart_failing=smart_failing,
            errors=disk_errors,
        ))

    return disks, current_io


def _get_network_interfaces(
    previous_io: dict[str, psutil._psplatform.NetIO] | None = None,
    elapsed_seconds: float = 1.0,
) -> tuple[list[NetworkInterfaceSnapshot], dict[str, psutil._psplatform.NetIO]]:
    interfaces: list[NetworkInterfaceSnapshot] = []
    current_io: dict[str, psutil._psplatform.NetIO] = {}
    try:
        current_io = psutil.net_io_counters(pernic=True) or {}
        stats = psutil.net_if_stats()
    except Exception:
        return interfaces, current_io

    total_sent_bps = 0.0
    total_recv_bps = 0.0

    for name, io in current_io.items():
        if name == "lo":
            continue
        stat = stats.get(name)
        prev_io = previous_io.get(name) if previous_io else None
        sent_bps = 0.0
        recv_bps = 0.0
        if prev_io and elapsed_seconds > 0:
            sent_bps = max(0.0, (io.bytes_sent - prev_io.bytes_sent) / elapsed_seconds)
            recv_bps = max(0.0, (io.bytes_recv - prev_io.bytes_recv) / elapsed_seconds)
        total_sent_bps += sent_bps
        total_recv_bps += recv_bps

        interfaces.append(NetworkInterfaceSnapshot(
            name=name,
            is_up=stat.isup if stat else False,
            speed_mbps=stat.speed if stat else None,
            mtu=stat.mtu if stat else 0,
            bytes_sent=io.bytes_sent,
            bytes_recv=io.bytes_recv,
            packets_sent=io.packets_sent,
            packets_recv=io.packets_recv,
            errin=io.errin,
            errout=io.errout,
            dropin=io.dropin,
            dropout=io.dropout,
            bytes_sent_per_sec=sent_bps,
            bytes_recv_per_sec=recv_bps,
        ))

    return interfaces, current_io


def get_network_snapshot(
    previous_io: dict[str, psutil._psplatform.NetIO] | None = None,
    elapsed_seconds: float = 1.0,
) -> NetworkSnapshot:
    interfaces, current_io = _get_network_interfaces(previous_io, elapsed_seconds)
    latency = None
    if shutil.which("ping"):
        rc, out, _ = _run(["ping", "-c", "1", "-W", "2", "1.1.1.1"], timeout=5)
        if rc == 0:
            for line in out.splitlines():
                if "time=" in line:
                    try:
                        latency = float(line.split("time=")[1].split()[0])
                    except Exception:
                        pass
    return NetworkSnapshot(
        interfaces=interfaces,
        total_bytes_sent_per_sec=sum(i.bytes_sent_per_sec for i in interfaces),
        total_bytes_recv_per_sec=sum(i.bytes_recv_per_sec for i in interfaces),
        latency_ms=latency,
    ), current_io


def _get_nvidia_gpus() -> list[GpuSnapshot]:
    gpus: list[GpuSnapshot] = []
    if not shutil.which("nvidia-smi"):
        return gpus
    rc, out, _ = _run([
        "nvidia-smi",
        "--query-gpu=name,utilization.gpu,temperature.gpu,memory.total,memory.used",
        "--format=csv,noheader,nounits",
    ])
    if rc != 0:
        return gpus
    for line in out.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 5:
            continue
        try:
            gpus.append(GpuSnapshot(
                name=parts[0],
                utilization_percent=float(parts[1]) if parts[1] else None,
                temperature_c=float(parts[2]) if parts[2] else None,
                memory_total_bytes=int(float(parts[3]) * 1024 * 1024) if parts[3] else None,
                memory_used_bytes=int(float(parts[4]) * 1024 * 1024) if parts[4] else None,
            ))
        except Exception:
            continue
    return gpus


def get_gpu_snapshots() -> list[GpuSnapshot]:
    try:
        return _get_nvidia_gpus()
    except Exception:
        return []


def get_uptime_seconds() -> float:
    try:
        return time.time() - psutil.boot_time()
    except Exception:
        return 0.0


def get_failed_services() -> list[str]:
    if not shutil.which("systemctl"):
        return []
    rc, out, _ = _run(["systemctl", "--failed", "--no-legend", "--plain", "--no-pager"])
    if rc != 0:
        return []
    failed: list[str] = []
    for line in out.splitlines():
        parts = line.split(None, 1)
        if parts and parts[0].endswith(".service"):
            failed.append(parts[0])
    return failed


def get_sensor_readings() -> list[SensorReading]:
    readings: list[SensorReading] = []
    try:
        temps = psutil.sensors_temperatures()
        for name, entries in temps.items():
            for entry in entries:
                readings.append(SensorReading(
                    label=f"{name}/{entry.label or 'temp'}",
                    value=float(entry.current) if entry.current is not None else None,
                    unit="°C",
                ))
    except Exception:
        pass
    try:
        fans = psutil.sensors_fans()
        for name, entries in fans.items():
            for entry in entries:
                readings.append(SensorReading(
                    label=f"{name}/{entry.label or 'fan'}",
                    value=float(entry.current) if entry.current is not None else None,
                    unit="RPM",
                ))
    except Exception:
        pass
    return readings


_update_cache: dict[str, object] = {"count": 0, "expires_at": 0.0}
_drive_health_cache: dict[str, object] = {"drives": [], "expires_at": 0.0}


def get_update_count() -> int:
    """Best-effort update count; returns 0 if unsupported or unknown.

    Cached for five minutes because package lists do not change second-to-second.
    """
    now = time.time()
    if now < _update_cache["expires_at"]:
        return int(_update_cache["count"])
    try:
        from app.services.updates import detect_updates
        result = detect_updates()
        _update_cache["count"] = result.update_count
        _update_cache["expires_at"] = now + 300
        return result.update_count
    except Exception:
        return 0


def get_drive_health_summary(include_smart: bool = True) -> list[dict]:
    """Return cached SMART health summary for physical drives.

    smartctl is slow, so results are cached for five minutes.
    """
    if not include_smart:
        return []
    now = time.time()
    if now < _drive_health_cache["expires_at"]:
        return list(_drive_health_cache["drives"])
    drives: list[dict] = []
    try:
        from app.services.storage import drive_to_dict, list_drives
        for info in list_drives():
            details = drive_to_dict(info)
            drives.append({
                "device": details["device"],
                "status": details["status"],
                "smart_status": details["smart_status"],
                "temperature_c": details["temperature_c"],
            })
    except Exception:
        pass
    _drive_health_cache["drives"] = drives
    _drive_health_cache["expires_at"] = now + 300
    return drives


class HealthCollector:
    """Collects health snapshots and computes deltas for live streaming."""

    def __init__(self) -> None:
        self._last_disk_io: dict[str, psutil._psplatform.DiskIO] = {}
        self._last_net_io: dict[str, psutil._psplatform.NetIO] = {}
        self._last_sample_time: float = time.time()

    def snapshot(self, include_smart: bool = False) -> HealthSnapshot:
        now = time.time()
        elapsed = max(0.001, now - self._last_sample_time)
        self._last_sample_time = now

        cpu = get_cpu_snapshot()
        memory = get_memory_snapshot()
        disks, self._last_disk_io = get_disk_snapshots(
            self._last_disk_io, elapsed, include_smart=include_smart
        )
        network, self._last_net_io = get_network_snapshot(self._last_net_io, elapsed)
        gpus = get_gpu_snapshots()
        uptime = get_uptime_seconds()
        failed = get_failed_services()
        fs_errors = _get_filesystem_errors()
        updates = get_update_count()
        sensors = get_sensor_readings()
        drives = [
            DriveHealthSummary(**d)
            for d in get_drive_health_summary(include_smart=include_smart)
        ]

        snapshot = HealthSnapshot(
            timestamp=now,
            cpu=cpu,
            memory=memory,
            disks=disks,
            drives=drives,
            network=network,
            gpus=gpus,
            uptime_seconds=uptime,
            failed_services=failed,
            filesystem_errors=fs_errors,
            update_count=updates,
            sensors=sensors,
        )
        snapshot.overall = calculate_overall_status(snapshot)
        return snapshot


def calculate_overall_status(snapshot: HealthSnapshot) -> str:
    """Return healthy/warning/critical based on component thresholds."""
    critical = 0
    warning = 0

    if snapshot.cpu.percent >= 95 or snapshot.cpu.temperature_c and snapshot.cpu.temperature_c >= 90:
        critical += 1
    elif snapshot.cpu.percent >= 80 or snapshot.cpu.temperature_c and snapshot.cpu.temperature_c >= 75:
        warning += 1

    if snapshot.memory.percent >= 90:
        critical += 1
    elif snapshot.memory.percent >= 80:
        warning += 1

    for disk in snapshot.disks:
        if disk.percent >= 95 or disk.smart_failing:
            critical += 1
        elif disk.percent >= 85 or disk.temperature_c and disk.temperature_c >= 60:
            warning += 1
        if disk.errors:
            warning += 1

    for drive in snapshot.drives:
        if drive.status == "critical":
            critical += 1
        elif drive.status == "warning" or drive.smart_status.lower() == "unknown":
            warning += 1

    for iface in snapshot.network.interfaces:
        # Skip interfaces that are down: their counters are historical.
        if not iface.is_up:
            continue
        # Errors are always meaningful; a handful of lifetime drops on virtual
        # bridges (docker, tailscale) is routine, so require a larger volume.
        if iface.errin or iface.errout or (iface.dropin + iface.dropout) > 1000:
            warning += 1

    if snapshot.failed_services:
        warning += 1

    if snapshot.filesystem_errors:
        critical += 1

    if snapshot.update_count > 50:
        warning += 1

    for gpu in snapshot.gpus:
        if gpu.temperature_c and gpu.temperature_c >= 90:
            critical += 1
        elif gpu.temperature_c and gpu.temperature_c >= 80:
            warning += 1

    if critical:
        return "critical"
    if warning:
        return "warning"
    return "healthy"


def snapshot_to_dict(snapshot: HealthSnapshot) -> dict:
    """Convert a HealthSnapshot to a JSON-serializable dict."""
    return {
        "timestamp": snapshot.timestamp,
        "overall": snapshot.overall,
        "cpu": {
            "percent": snapshot.cpu.percent,
            "per_cpu": snapshot.cpu.per_cpu,
            "load_1": snapshot.cpu.load_1,
            "load_5": snapshot.cpu.load_5,
            "load_15": snapshot.cpu.load_15,
            "frequency_mhz": snapshot.cpu.frequency_mhz,
            "temperature_c": snapshot.cpu.temperature_c,
        },
        "memory": {
            "total_bytes": snapshot.memory.total_bytes,
            "used_bytes": snapshot.memory.used_bytes,
            "available_bytes": snapshot.memory.available_bytes,
            "percent": snapshot.memory.percent,
            "swap_total_bytes": snapshot.memory.swap_total_bytes,
            "swap_used_bytes": snapshot.memory.swap_used_bytes,
            "swap_percent": snapshot.memory.swap_percent,
        },
        "disks": [
            {
                "device": d.device,
                "mountpoint": d.mountpoint,
                "fstype": d.fstype,
                "total_bytes": d.total_bytes,
                "used_bytes": d.used_bytes,
                "free_bytes": d.free_bytes,
                "percent": d.percent,
                "read_bytes_per_sec": d.read_bytes_per_sec,
                "write_bytes_per_sec": d.write_bytes_per_sec,
                "iops": d.iops,
                "temperature_c": d.temperature_c,
                "smart_status": d.smart_status,
                "smart_failing": d.smart_failing,
                "errors": d.errors,
            }
            for d in snapshot.disks
        ],
        "drives": [
            {
                "device": d.device,
                "status": d.status,
                "smart_status": d.smart_status,
                "temperature_c": d.temperature_c,
            }
            for d in snapshot.drives
        ],
        "network": {
            "total_bytes_sent_per_sec": snapshot.network.total_bytes_sent_per_sec,
            "total_bytes_recv_per_sec": snapshot.network.total_bytes_recv_per_sec,
            "latency_ms": snapshot.network.latency_ms,
            "interfaces": [
                {
                    "name": i.name,
                    "is_up": i.is_up,
                    "speed_mbps": i.speed_mbps,
                    "mtu": i.mtu,
                    "bytes_sent": i.bytes_sent,
                    "bytes_recv": i.bytes_recv,
                    "packets_sent": i.packets_sent,
                    "packets_recv": i.packets_recv,
                    "errin": i.errin,
                    "errout": i.errout,
                    "dropin": i.dropin,
                    "dropout": i.dropout,
                    "bytes_sent_per_sec": i.bytes_sent_per_sec,
                    "bytes_recv_per_sec": i.bytes_recv_per_sec,
                }
                for i in snapshot.network.interfaces
            ],
        },
        "gpus": [
            {
                "name": g.name,
                "utilization_percent": g.utilization_percent,
                "temperature_c": g.temperature_c,
                "memory_total_bytes": g.memory_total_bytes,
                "memory_used_bytes": g.memory_used_bytes,
            }
            for g in snapshot.gpus
        ],
        "uptime_seconds": snapshot.uptime_seconds,
        "failed_services": snapshot.failed_services,
        "filesystem_errors": snapshot.filesystem_errors,
        "update_count": snapshot.update_count,
        "sensors": [
            {"label": s.label, "value": s.value, "unit": s.unit}
            for s in snapshot.sensors
        ],
    }
