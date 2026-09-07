"""systemd service discovery and management helpers."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class ServiceSummary:
    """Brief service information for list views."""

    name: str
    description: str
    load_state: str
    active_state: str
    sub_state: str
    unit_file_state: str
    main_pid: int = 0
    memory_current: Optional[int] = None
    cpu_usage_nsec: Optional[int] = None
    tasks_current: Optional[int] = None
    state_change_timestamp: Optional[datetime] = None
    is_system_service: bool = False

    @property
    def status(self) -> str:
        if self.active_state == "failed":
            return "failed"
        if self.active_state == "active":
            return "running"
        if self.active_state == "inactive":
            return "stopped"
        return self.active_state or "unknown"

    @property
    def enabled(self) -> bool:
        return self.unit_file_state in {"enabled", "enabled-runtime", "static", "generated", "transient"}


@dataclass
class ServiceDetail(ServiceSummary):
    """Detailed service information for the service detail page."""

    names: list[str] = field(default_factory=list)
    user: Optional[str] = None
    group: Optional[str] = None
    restart: str = ""
    restart_usec: int = 0
    fragment_path: str = ""
    source_path: str = ""
    drop_in_paths: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    requisite: list[str] = field(default_factory=list)
    wants: list[str] = field(default_factory=list)
    binds_to: list[str] = field(default_factory=list)
    part_of: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    before: list[str] = field(default_factory=list)
    after: list[str] = field(default_factory=list)
    on_failure: list[str] = field(default_factory=list)
    refuses_manual_start: bool = False
    refuses_manual_stop: bool = False
    can_start: bool = True
    can_stop: bool = True
    can_reload: bool = False
    can_restart: bool = True


def _run(cmd: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    """Run a command safely without shell interpolation."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def systemctl_available() -> bool:
    """Check whether systemctl is available on the system."""
    return shutil.which("systemctl") is not None


def _is_system_service(name: str, description: str) -> bool:
    """Heuristic to classify a service as a system/internal service."""
    lower_name = name.lower()
    lower_desc = description.lower()
    system_prefixes = (
        "systemd-",
        "dbus-",
        "user@",
        "session-",
        "getty@",
        "ifupdown-",
        "apt-daily",
        "logrotate",
        "man-db",
        "e2scrub_",
    )
    if lower_name.startswith(system_prefixes):
        return True
    if "systemd" in lower_desc and "user" not in lower_desc:
        return True
    return False


def _parse_usec_timestamp(value: str) -> Optional[datetime]:
    """Parse a systemd microsecond timestamp into a UTC datetime."""
    if not value or value in {"0", "n/a"}:
        return None
    try:
        # systemd timestamps are microseconds since the Unix epoch in UTC.
        us = int(value)
        return datetime.fromtimestamp(us / 1_000_000, tz=timezone.utc)
    except ValueError:
        return None


def _parse_int(value: str) -> Optional[int]:
    if not value or value.lower() in {"n/a", "(null)", "0"}:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _split_space_list(value: str) -> list[str]:
    """Split a systemd space-separated property value into a list."""
    if not value or value == "":
        return []
    return [item.strip() for item in value.split() if item.strip()]


def _systemctl_show_properties(unit: str) -> dict[str, str]:
    """Return a dict of properties from systemctl show for a unit."""
    props = [
        "Id",
        "Names",
        "Description",
        "LoadState",
        "ActiveState",
        "SubState",
        "UnitFileState",
        "MainPID",
        "MemoryCurrent",
        "CPUUsageNSec",
        "TasksCurrent",
        "StateChangeTimestamp",
        "InactiveExitTimestamp",
        "ActiveEnterTimestamp",
        "ActiveExitTimestamp",
        "InactiveEnterTimestamp",
        "ExecMainStartTimestamp",
        "User",
        "Group",
        "Restart",
        "RestartUSec",
        "FragmentPath",
        "SourcePath",
        "DropInPaths",
        "Requires",
        "Requisite",
        "Wants",
        "BindsTo",
        "PartOf",
        "Conflicts",
        "Before",
        "After",
        "OnFailure",
        "RefuseManualStart",
        "RefuseManualStop",
        "CanStart",
        "CanStop",
        "CanReload",
        "CanRestart",
    ]
    cmd = ["systemctl", "show", unit, "--no-pager"] + [f"--property={p}" for p in props]
    result = _run(cmd)
    properties: dict[str, str] = {}
    if result.returncode != 0:
        return properties
    for line in result.stdout.splitlines():
        if "=" in line:
            key, val = line.split("=", 1)
            properties[key] = val
    return properties


def _build_service_summary(props: dict[str, str]) -> ServiceSummary:
    name = props.get("Id", "")
    description = props.get("Description", "")
    return ServiceSummary(
        name=name,
        description=description,
        load_state=props.get("LoadState", ""),
        active_state=props.get("ActiveState", ""),
        sub_state=props.get("SubState", ""),
        unit_file_state=props.get("UnitFileState", ""),
        main_pid=_parse_int(props.get("MainPID")) or 0,
        memory_current=_parse_int(props.get("MemoryCurrent")),
        cpu_usage_nsec=_parse_int(props.get("CPUUsageNSec")),
        tasks_current=_parse_int(props.get("TasksCurrent")),
        state_change_timestamp=_parse_usec_timestamp(props.get("StateChangeTimestamp")),
        is_system_service=_is_system_service(name, description),
    )


def _build_service_detail(props: dict[str, str]) -> ServiceDetail:
    summary = _build_service_summary(props)
    return ServiceDetail(
        **summary.__dict__,
        names=_split_space_list(props.get("Names", "")),
        user=props.get("User") or None,
        group=props.get("Group") or None,
        restart=props.get("Restart", ""),
        restart_usec=_parse_int(props.get("RestartUSec")) or 0,
        fragment_path=props.get("FragmentPath", ""),
        source_path=props.get("SourcePath", ""),
        drop_in_paths=_split_space_list(props.get("DropInPaths", "")),
        requires=_split_space_list(props.get("Requires", "")),
        requisite=_split_space_list(props.get("Requisite", "")),
        wants=_split_space_list(props.get("Wants", "")),
        binds_to=_split_space_list(props.get("BindsTo", "")),
        part_of=_split_space_list(props.get("PartOf", "")),
        conflicts=_split_space_list(props.get("Conflicts", "")),
        before=_split_space_list(props.get("Before", "")),
        after=_split_space_list(props.get("After", "")),
        on_failure=_split_space_list(props.get("OnFailure", "")),
        refuses_manual_start=props.get("RefuseManualStart", "no").lower() == "yes",
        refuses_manual_stop=props.get("RefuseManualStop", "no").lower() == "yes",
        can_start=props.get("CanStart", "yes").lower() == "yes",
        can_stop=props.get("CanStop", "yes").lower() == "yes",
        can_reload=props.get("CanReload", "no").lower() == "yes",
        can_restart=props.get("CanRestart", "yes").lower() == "yes",
    )


def list_services(
    show_system: bool = False,
    state_filter: Optional[str] = None,
    search: Optional[str] = None,
) -> list[ServiceSummary]:
    """Discover systemd services and return summaries."""
    cmd = [
        "systemctl",
        "list-units",
        "--type=service",
        "--all",
        "--full",
        "--plain",
        "--no-pager",
        "--no-legend",
    ]
    result = _run(cmd, timeout=60)
    if result.returncode != 0:
        return []

    services: list[ServiceSummary] = []
    search_lower = search.lower() if search else None

    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        # Lines look like:
        # nginx.service loaded active running A high performance web server...
        parts = line.split(None, 4)
        if len(parts) < 4:
            continue
        name = parts[0]
        # Skip non-.service units and synthetic entries.
        if not name.endswith(".service"):
            continue
        description = parts[4] if len(parts) > 4 else ""

        if search_lower and not (
            search_lower in name.lower() or search_lower in description.lower()
        ):
            continue

        props = _systemctl_show_properties(name)
        if not props:
            continue

        summary = _build_service_summary(props)

        if not show_system and summary.is_system_service:
            continue

        if state_filter:
            if state_filter == "failed" and summary.active_state != "failed":
                continue
            if state_filter == "active" and summary.active_state != "active":
                continue
            if state_filter == "inactive" and summary.active_state != "inactive":
                continue
            if state_filter == "running" and summary.sub_state != "running":
                continue

        services.append(summary)

    return services


def get_service_detail(service: str) -> Optional[ServiceDetail]:
    """Return detailed information for a single service."""
    if not service.endswith(".service"):
        service = f"{service}.service"
    props = _systemctl_show_properties(service)
    if not props or not props.get("Id"):
        return None
    return _build_service_detail(props)


def perform_service_action(service: str, action: str) -> tuple[bool, str]:
    """Perform start/stop/restart/reload/enable/disable on a service.

    Requires the calling Linux user to have passwordless sudo for these
    specific systemctl subcommands.
    """
    allowed_actions = {"start", "stop", "restart", "reload", "enable", "disable"}
    if action not in allowed_actions:
        raise ValueError(f"Action '{action}' is not allowed")

    if not service.endswith(".service"):
        service = f"{service}.service"

    cmd = ["sudo", "-n", "systemctl", action, service]
    result = _run(cmd, timeout=120)
    success = result.returncode == 0
    message = result.stdout.strip() or result.stderr.strip() or "completed"
    return success, message


def get_service_uptime_seconds(detail: ServiceDetail) -> Optional[float]:
    """Calculate service uptime in seconds from systemd timestamps."""
    if detail.active_state == "active" and detail.state_change_timestamp:
        return (datetime.now(timezone.utc) - detail.state_change_timestamp).total_seconds()
    return None
