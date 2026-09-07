"""Log reading helpers using journalctl."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class LogEntry:
    timestamp: Optional[str]
    priority: int
    priority_name: str
    unit: str
    identifier: str
    message: str


_PRIORITY_NAMES = {
    "0": "emerg",
    "1": "alert",
    "2": "crit",
    "3": "err",
    "4": "warning",
    "5": "notice",
    "6": "info",
    "7": "debug",
}


def journalctl_available() -> bool:
    return shutil.which("journalctl") is not None


def _validate_unit_name(unit: str) -> str:
    """Validate and normalize a systemd unit name."""
    unit = unit.strip()
    if not unit:
        raise ValueError("Unit name is required")
    if not re.fullmatch(r"[A-Za-z0-9_.\-@]+\.service", unit):
        raise ValueError(f"Invalid unit name: {unit}")
    return unit


def _parse_timestamp_us(value: str | None) -> Optional[str]:
    if not value:
        return None
    try:
        us = int(value)
        dt = datetime.fromtimestamp(us / 1_000_000, tz=timezone.utc)
        return dt.isoformat()
    except ValueError:
        return None


def read_logs(
    unit: str,
    limit: int = 200,
    since: Optional[str] = None,
    until: Optional[str] = None,
    priority: Optional[int] = None,
) -> list[LogEntry]:
    """Read journal logs for a specific unit."""
    unit = _validate_unit_name(unit)

    cmd = [
        "journalctl",
        "-u",
        unit,
        "--no-pager",
        "--output=json",
        f"--lines={max(1, min(limit, 5000))}",
    ]
    if since:
        cmd.extend(["--since", since])
    if until:
        cmd.extend(["--until", until])
    if priority is not None and 0 <= priority <= 7:
        cmd.extend(["--priority", str(priority)])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    if result.returncode != 0:
        # journalctl returns non-zero when there are no logs for the unit.
        if "No journal files were found" in result.stderr:
            return []
        # Treat other errors as empty logs rather than failing the whole request.
        return []

    entries: list[LogEntry] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        # Use realtime timestamp if available, fallback to source realtime.
        ts = _parse_timestamp_us(record.get("__REALTIME_TIMESTAMP"))
        if ts is None:
            ts = _parse_timestamp_us(record.get("_SOURCE_REALTIME_TIMESTAMP"))

        priority_str = record.get("PRIORITY", "6")
        priority_int = int(priority_str) if priority_str.isdigit() else 6

        entries.append(
            LogEntry(
                timestamp=ts,
                priority=priority_int,
                priority_name=_PRIORITY_NAMES.get(str(priority_int), "info"),
                unit=record.get("_SYSTEMD_UNIT", unit),
                identifier=record.get("SYSLOG_IDENTIFIER", "") or record.get("_COMM", ""),
                message=record.get("MESSAGE", ""),
            )
        )

    return entries
