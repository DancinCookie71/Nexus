"""Process listing and control via psutil."""
from __future__ import annotations

import os
import signal
from typing import Optional

import psutil


class ProcessError(Exception):
    """Raised when a process cannot be listed or signaled."""


_PROTECTED_PIDS = {1, 2}
_MAX_LIST = 1000


def _service_username() -> str:
    import pwd

    try:
        return pwd.getpwuid(os.getuid()).pw_name
    except KeyError:
        return str(os.getuid())


def list_processes(limit: int = 200) -> dict:
    """Return a snapshot of system processes sorted by CPU usage."""
    processes: list[dict] = []
    for proc in psutil.process_iter(
        ["pid", "name", "username", "cpu_percent", "memory_percent", "memory_info", "status", "cmdline"]
    ):
        try:
            info = proc.info
            mem = info.get("memory_info")
            cmdline = " ".join(info.get("cmdline") or [])
            processes.append(
                {
                    "pid": info["pid"],
                    "name": info.get("name") or "?",
                    "username": info.get("username") or "?",
                    "cpu_percent": float(info.get("cpu_percent") or 0.0),
                    "memory_percent": round(float(info.get("memory_percent") or 0.0), 1),
                    "memory_bytes": mem.rss if mem else 0,
                    "status": info.get("status") or "?",
                    "command": (cmdline or info.get("name") or "?")[:300],
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    processes.sort(key=lambda p: (p["cpu_percent"], p["memory_percent"], -p["pid"]), reverse=True)
    vm = psutil.virtual_memory()
    return {
        "processes": processes[: max(1, min(limit, _MAX_LIST))],
        "total": len(processes),
        "running": sum(1 for p in processes if p["status"] == psutil.STATUS_RUNNING),
        "sleeping": sum(1 for p in processes if p["status"] == psutil.STATUS_SLEEPING),
        "cpu_percent": psutil.cpu_percent(interval=None),
        "memory_percent": vm.percent,
        "load_average": [round(x, 2) for x in psutil.getloadavg()],
    }


def kill_process(pid: int, signame: str = "TERM") -> None:
    """Signal a process owned by the service user. Protected processes are rejected."""
    if pid in _PROTECTED_PIDS or pid == os.getpid() or pid == os.getppid():
        raise ProcessError("This process cannot be stopped")
    try:
        proc = psutil.Process(pid)
    except psutil.NoSuchProcess:
        raise ProcessError("Process not found")
    if proc.username() != _service_username():
        raise ProcessError("Process belongs to another user")

    sig = signal.SIGTERM if signame == "TERM" else signal.SIGKILL
    try:
        proc.send_signal(sig)
        proc.wait(timeout=5)
    except psutil.NoSuchProcess:
        return
    except psutil.TimeoutExpired:
        if sig == signal.SIGTERM:
            try:
                proc.kill()
                proc.wait(timeout=3)
            except psutil.TimeoutExpired:
                raise ProcessError("Process did not terminate")
            except psutil.NoSuchProcess:
                return
        else:
            raise ProcessError("Process did not terminate")
    except psutil.AccessDenied:
        raise ProcessError("Permission denied")
