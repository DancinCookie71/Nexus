"""Safe package-update detection and application."""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class UpdateResult:
    supported: bool
    package_manager: Optional[str]
    update_count: int
    packages: list[str]
    error: Optional[str]
    last_checked: Optional[str]
    reboot_required: bool = False


@dataclass
class ApplyResult:
    success: bool
    message: str
    reboot_scheduled: bool = False


def _run(cmd: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _reboot_required() -> bool:
    """Debian/RPi OS leaves a flag file when the system needs a restart."""
    return os.path.exists("/var/run/reboot-required")


def _detect_apt_updates() -> UpdateResult:
    """Detect available updates using apt (Debian/Ubuntu/Raspberry Pi OS)."""
    # Use apt list --upgradable which is read-only and fast.
    result = _run(["apt", "list", "--upgradable", "-qq"])
    if result.returncode != 0:
        return UpdateResult(
            supported=True,
            package_manager="apt",
            update_count=0,
            packages=[],
            error=result.stderr.strip() or "apt returned an error",
            last_checked=_now_iso(),
        reboot_required=_reboot_required(),
        )

    packages = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("Listing") or line.startswith("N:") or line.startswith("W:"):
            continue
        # Format: package/name version arch [upgradable from: ...]
        parts = line.split("/")
        if parts and parts[0]:
            packages.append(parts[0])

    packages = sorted(set(packages))
    return UpdateResult(
        supported=True,
        package_manager="apt",
        update_count=len(packages),
        packages=packages,
        error=None,
        last_checked=_now_iso(),
        reboot_required=_reboot_required(),
    )


def _detect_dnf_updates() -> UpdateResult:
    """Detect available updates using dnf (RHEL/Fedora)."""
    result = _run(["dnf", "check-update", "-q"])
    # dnf returns 100 when updates are available.
    if result.returncode not in (0, 100):
        return UpdateResult(
            supported=True,
            package_manager="dnf",
            update_count=0,
            packages=[],
            error=result.stderr.strip() or "dnf returned an error",
            last_checked=_now_iso(),
        reboot_required=_reboot_required(),
        )

    packages = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("=") or "packages" in line.lower():
            continue
        parts = line.split()
        if parts:
            packages.append(parts[0])

    packages = sorted(set(packages))
    return UpdateResult(
        supported=True,
        package_manager="dnf",
        update_count=len(packages),
        packages=packages,
        error=None,
        last_checked=_now_iso(),
        reboot_required=_reboot_required(),
    )


def detect_updates() -> UpdateResult:
    """Detect available system package updates safely."""
    if shutil.which("apt"):
        return _detect_apt_updates()
    if shutil.which("dnf"):
        return _detect_dnf_updates()

    return UpdateResult(
        supported=False,
        package_manager=None,
        update_count=0,
        packages=[],
        error="No supported package manager detected (apt or dnf).",
        last_checked=_now_iso(),
        reboot_required=_reboot_required(),
    )


def _package_manager() -> Optional[str]:
    if shutil.which("apt"):
        return "apt"
    if shutil.which("dnf"):
        return "dnf"
    return None


def apply_updates(reboot: bool = False) -> ApplyResult:
    """Apply all available system updates for the detected package manager.

    Optionally schedules a reboot after successful installation.
    """
    manager = _package_manager()
    if manager is None:
        return ApplyResult(
            success=False,
            message="No supported package manager detected (apt or dnf).",
        )

    if manager == "apt":
        # Command lines must match the NEXUS_UPDATES sudoers alias exactly.
        update_result = _run(["sudo", "-n", "apt-get", "update"], timeout=300)
        if update_result.returncode != 0:
            return ApplyResult(
                success=False,
                message=f"apt update failed: {update_result.stderr.strip() or 'unknown error'}",
            )
        upgrade_result = _run(
            ["sudo", "-n", "DEBIAN_FRONTEND=noninteractive", "apt-get", "-y", "upgrade"],
            timeout=3600,
        )
    else:  # dnf
        upgrade_result = _run(
            ["sudo", "-n", "dnf", "upgrade", "-y"],
            timeout=1800,
        )

    if upgrade_result.returncode != 0:
        return ApplyResult(
            success=False,
            message=f"{manager} upgrade failed: {upgrade_result.stderr.strip() or upgrade_result.stdout.strip() or 'unknown error'}",
        )

    if reboot:
        reboot_result = _run(["sudo", "-n", "systemctl", "reboot"], timeout=30)
        if reboot_result.returncode != 0:
            return ApplyResult(
                success=True,
                message=f"Updates installed successfully, but reboot scheduling failed: {reboot_result.stderr.strip() or 'unknown error'}",
            )
        return ApplyResult(
            success=True,
            message="Updates installed successfully. The system is rebooting now.",
            reboot_scheduled=True,
        )

    return ApplyResult(
        success=True,
        message="Updates installed successfully.",
    )


def reboot_system() -> ApplyResult:
    """Reboot the system immediately."""
    result = _run(["sudo", "-n", "systemctl", "reboot"], timeout=30)
    if result.returncode != 0:
        return ApplyResult(
            success=False,
            message=f"Failed to schedule reboot: {result.stderr.strip() or 'unknown error'}",
        )
    return ApplyResult(
        success=True,
        message="The system is rebooting now.",
        reboot_scheduled=True,
    )
