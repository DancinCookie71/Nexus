"""Physical drive discovery and SMART health analysis."""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SmartAttribute:
    id: int
    name: str
    flag: str
    value: int | None
    worst: int | None
    threshold: int | None
    attr_type: str
    updated: str
    when_failed: str
    raw_value: str


@dataclass
class DriveInfo:
    device: str
    model: str = ""
    serial: str = ""
    firmware: str = ""
    size_bytes: int = 0
    size_human: str = ""
    rotation_rate: int | None = None
    is_ssd: bool = False
    smart_supported: bool = False
    smart_enabled: bool = False
    smart_status: str = "unknown"
    temperature_c: int | None = None
    power_on_hours: int | None = None
    attributes: list[SmartAttribute] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)


def _run(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
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


def _find_smartctl() -> str:
    return shutil.which("smartctl") or "/usr/sbin/smartctl"


def _smartctl_cmd(device: str, args: list[str], device_type: str | None = None, use_sudo: bool = False) -> list[str]:
    cmd = ["sudo", "-n", _find_smartctl()] if use_sudo else [_find_smartctl()]
    cmd.extend(args)
    if device_type:
        cmd.extend(["-d", device_type])
    cmd.append(device)
    return cmd


def _try_smart_with_types(device: str, args: list[str], use_sudo: bool) -> tuple[int, str, str, str | None]:
    """Try smartctl with optional device types for USB bridges."""
    rc, out, err = _run(_smartctl_cmd(device, args, use_sudo=use_sudo))
    if rc == 0:
        return rc, out, err, None
    err_lower = (err + out).lower()
    if "unknown usb bridge" in err_lower or "permission denied" in err_lower:
        for dtype in ("sat", "auto", "usbcypress", "usbjmicron", "usbprolific", "usbsunplus"):
            rc2, out2, err2 = _run(_smartctl_cmd(device, args, device_type=dtype, use_sudo=use_sudo))
            if rc2 == 0:
                return rc2, out2, err2, dtype
    return rc, out, err, None


def _try_smartctl(device: str, args: list[str]) -> tuple[int, str, str, str | None]:
    """Try smartctl as root via sudo first, then fall back to the current user."""
    sudo_available = shutil.which("sudo") is not None
    if sudo_available:
        rc, out, err, dtype = _try_smart_with_types(device, args, use_sudo=True)
        if rc == 0:
            return rc, out, err, dtype
    return _try_smart_with_types(device, args, use_sudo=False)


def _parse_smart_attributes(output: str) -> list[SmartAttribute]:
    attrs: list[SmartAttribute] = []
    in_attrs = False
    for line in output.splitlines():
        if "ID#" in line and "ATTRIBUTE_NAME" in line:
            in_attrs = True
            continue
        if not in_attrs:
            continue
        parts = line.split()
        if len(parts) < 10:
            continue
        try:
            attr_id = int(parts[0])
        except ValueError:
            continue
        name = parts[1]
        flag = parts[2]
        try:
            value = int(parts[3])
            worst = int(parts[4])
            threshold = int(parts[5])
        except ValueError:
            value = worst = threshold = None
        attr_type = parts[6]
        updated = parts[7]
        when_failed = parts[8]
        raw_value = " ".join(parts[9:])
        attrs.append(SmartAttribute(
            id=attr_id,
            name=name,
            flag=flag,
            value=value,
            worst=worst,
            threshold=threshold,
            attr_type=attr_type,
            updated=updated,
            when_failed=when_failed,
            raw_value=raw_value,
        ))
    return attrs


def _extract_int_field(output: str, key: str) -> int | None:
    for line in output.splitlines():
        if line.startswith(key):
            try:
                return int(line.split(":", 1)[1].strip().split()[0])
            except Exception:
                return None
    return None


def _extract_temperature(attributes: list[SmartAttribute], info_output: str) -> int | None:
    for attr in attributes:
        if "temperature" in attr.name.lower() or attr.name == "Airflow_Temperature_Cel":
            try:
                return int(attr.raw_value.split()[0])
            except Exception:
                pass
    # Fallback to info output.
    for line in info_output.splitlines():
        if "temperature" in line.lower() and ":" in line:
            try:
                return int(line.split(":", 1)[1].strip().split()[0])
            except Exception:
                pass
    return None


def _extract_power_on_hours(attributes: list[SmartAttribute]) -> int | None:
    for attr in attributes:
        if attr.name == "Power_On_Hours":
            try:
                return int(attr.raw_value.split()[0])
            except Exception:
                return None
    return None


def _extract_smart_status(output: str) -> str:
    for line in output.splitlines():
        lower = line.lower()
        if "smart overall-health" in lower and "result:" in lower:
            return line.split(":", 1)[1].strip()
    return "unknown"


def _drive_status(info: DriveInfo) -> str:
    """Calculate overall drive status from SMART data."""
    if info.smart_status.lower() == "failed":
        return "critical"

    if info.smart_status.lower() == "unknown" and not info.attributes:
        return "warning"

    critical_attrs = {
        "Reallocated_Sector_Ct",
        "Used_Rsvd_Blk_Cnt_Tot",
        "Runtime_Bad_Block",
        "Uncorrectable_Error_Cnt",
        "Current_Pending_Sector",
        "Offline_Uncorrectable",
    }
    for attr in info.attributes:
        if attr.when_failed and "-" not in attr.when_failed:
            return "critical"
        if attr.name in critical_attrs:
            try:
                raw = int(attr.raw_value.split()[0])
                if raw > 0:
                    return "critical"
            except Exception:
                pass
        if attr.threshold is not None and attr.value is not None and attr.attr_type == "Pre-fail":
            if attr.value <= attr.threshold:
                return "critical"

    if info.temperature_c is not None and info.temperature_c >= 70:
        return "critical"
    if info.temperature_c is not None and info.temperature_c >= 55:
        return "warning"

    return "healthy"


def examine_drive(device: str) -> DriveInfo:
    """Return detailed SMART information for a single drive."""
    info = DriveInfo(device=device)

    if not shutil.which("smartctl") and not shutil.which("/usr/sbin/smartctl"):
        info.messages.append("smartctl is not installed")
        return info

    # Basic info.
    rc, out, err, dtype = _try_smartctl(device, ["-i"])
    if rc != 0:
        info.messages.append(f"smartctl -i failed: {err or out}")
        return info

    for line in out.splitlines():
        if line.startswith("Device Model:"):
            info.model = line.split(":", 1)[1].strip()
        elif line.startswith("Serial Number:"):
            info.serial = line.split(":", 1)[1].strip()
        elif line.startswith("Firmware Version:"):
            info.firmware = line.split(":", 1)[1].strip()
        elif line.startswith("User Capacity:"):
            # Format: "User Capacity:    500,107,862,016 bytes [500 GB]"
            try:
                parts = line.split("[", 1)
                bytes_part = parts[0].split(":", 1)[1].strip()
                info.size_human = parts[1].split("]", 1)[0].strip() if len(parts) > 1 else ""
                info.size_bytes = int(bytes_part.replace(",", "").replace(" bytes", ""))
            except Exception:
                pass
        elif line.startswith("Rotation Rate:"):
            try:
                info.rotation_rate = int(line.split(":", 1)[1].strip().split()[0])
            except Exception:
                info.rotation_rate = 0
        elif "solid state" in line.lower() or "ssd" in line.lower():
            info.is_ssd = True
        elif line.startswith("SMART support is:") and "Available" in line:
            info.smart_supported = True
        elif line.startswith("SMART support is:") and "Enabled" in line:
            info.smart_enabled = True

    # Health self-assessment.
    rc2, out2, err2, _ = _try_smartctl(device, ["-H"])
    if rc2 == 0:
        info.smart_status = _extract_smart_status(out2)
    else:
        info.messages.append(f"smartctl -H failed: {err2 or out2}")

    # Full attributes.
    rc3, out3, err3, _ = _try_smartctl(device, ["-A"])
    if rc3 == 0:
        info.attributes = _parse_smart_attributes(out3)
    else:
        info.messages.append(f"smartctl -A failed: {err3 or out3}")

    info.temperature_c = _extract_temperature(info.attributes, out)
    info.power_on_hours = _extract_power_on_hours(info.attributes)

    return info


def list_drives() -> list[DriveInfo]:
    """Discover physical drives using lsblk and basic smartctl info."""
    drives: list[DriveInfo] = []
    if not shutil.which("lsblk"):
        return drives

    rc, out, _ = _run(["lsblk", "-d", "-J", "-o", "NAME,SIZE,TYPE,MODEL,STATE,ROTA"])
    if rc != 0 or not out:
        return drives

    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return drives

    for entry in data.get("blockdevices", []):
        name = entry.get("name", "")
        if entry.get("type") != "disk" or name.startswith(("loop", "zram", "ram")):
            continue
        device = f"/dev/{name}"
        info = examine_drive(device)
        if not info.model:
            info.model = entry.get("model") or "Unknown"
        if not info.size_human:
            info.size_human = entry.get("size") or ""
        if info.size_bytes == 0:
            size_b = entry.get("size")
            if isinstance(size_b, int):
                info.size_bytes = size_b
        if info.rotation_rate is None:
            rota = entry.get("rota")
            if rota is False:
                info.is_ssd = True
                info.rotation_rate = 0
            elif rota is True:
                info.rotation_rate = 1
        drives.append(info)

    return drives


def drive_to_dict(info: DriveInfo) -> dict:
    return {
        "device": info.device,
        "model": info.model,
        "serial": info.serial,
        "firmware": info.firmware,
        "size_bytes": info.size_bytes,
        "size_human": info.size_human,
        "rotation_rate": info.rotation_rate,
        "is_ssd": info.is_ssd,
        "smart_supported": info.smart_supported,
        "smart_enabled": info.smart_enabled,
        "smart_status": info.smart_status,
        "temperature_c": info.temperature_c,
        "power_on_hours": info.power_on_hours,
        "status": _drive_status(info),
        "attributes": [
            {
                "id": a.id,
                "name": a.name,
                "flag": a.flag,
                "value": a.value,
                "worst": a.worst,
                "threshold": a.threshold,
                "type": a.attr_type,
                "updated": a.updated,
                "when_failed": a.when_failed,
                "raw_value": a.raw_value,
            }
            for a in info.attributes
        ],
        "messages": info.messages,
    }
