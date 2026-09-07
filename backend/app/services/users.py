"""Local UNIX account management, Cockpit-accounts style."""
from __future__ import annotations

import pwd
import subprocess
from typing import Optional

from app.auth import _valid_linux_username, is_reserved_username


class UserManagementError(Exception):
    """Raised when an account management operation cannot be performed."""


_SUDO_GROUPS = ("sudo", "wheel")
_BLOCKED_SHELLS = {"nologin", "false"}


def _run(cmd: list[str], input_text: Optional[str] = None, timeout: int = 30) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        ["sudo", "-n", *cmd],
        input=input_text,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        raise UserManagementError(proc.stderr.strip() or f"{cmd[0]} failed")
    return proc


def _available_shells() -> list[str]:
    shells = []
    try:
        with open("/etc/shells", "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#"):
                    shells.append(line)
    except OSError:
        pass
    return shells or ["/bin/bash"]


def _validate_shell(shell: str) -> None:
    if shell not in _available_shells():
        raise UserManagementError("Shell is not listed in /etc/shells")


def _is_admin_user(username: str, primary_gid: int) -> bool:
    import grp

    for group_name in _SUDO_GROUPS:
        try:
            group = grp.getgrnam(group_name)
        except KeyError:
            continue
        if username in group.gr_mem or primary_gid == group.gr_gid:
            return True
    return False


def _get_entry(username: str) -> pwd.struct_passwd:
    try:
        return pwd.getpwnam(username)
    except KeyError:
        raise UserManagementError("User not found")


def list_unix_users() -> list[dict]:
    """Return human (UID >= 1000, real shell) local accounts."""
    users = []
    for entry in pwd.getpwall():
        shell_base = entry.pw_shell.rsplit("/", 1)[-1].lower() if entry.pw_shell else ""
        if entry.pw_uid < 1000 or shell_base in _BLOCKED_SHELLS:
            continue
        users.append(
            {
                "username": entry.pw_name,
                "full_name": entry.pw_gecos.split(",")[0] if entry.pw_gecos else "",
                "home": entry.pw_dir,
                "shell": entry.pw_shell,
                "uid": entry.pw_uid,
                "is_admin": _is_admin_user(entry.pw_name, entry.pw_gid),
            }
        )
    users.sort(key=lambda u: u["username"])
    return users


def create_unix_user(username: str, full_name: str, password: str, shell: str = "/bin/bash") -> None:
    if not _valid_linux_username(username):
        raise UserManagementError("Invalid username (lowercase letters, digits, - and _)")
    if is_reserved_username(username):
        raise UserManagementError("Username is reserved")
    if len(password) < 8:
        raise UserManagementError("Password must be at least 8 characters")
    _validate_shell(shell)
    try:
        pwd.getpwnam(username)
        raise UserManagementError("User already exists")
    except KeyError:
        pass
    _run(["useradd", "-m", "-c", full_name, "-s", shell, username])
    try:
        set_unix_password(username, password)
    except UserManagementError:
        _run(["userdel", username])
        raise


def set_unix_password(username: str, password: str) -> None:
    if len(password) < 8:
        raise UserManagementError("Password must be at least 8 characters")
    _get_entry(username)
    _run(["chpasswd"], input_text=f"{username}:{password}\n")


def delete_unix_user(username: str, operator_username: Optional[str]) -> None:
    if operator_username and username == operator_username:
        raise UserManagementError("You cannot delete the account you are operating as")
    _get_entry(username)
    _run(["userdel", username])


def set_admin_membership(username: str, make_admin: bool, operator_username: Optional[str]) -> None:
    _get_entry(username)
    if not make_admin and operator_username and username == operator_username:
        raise UserManagementError("You cannot remove your own admin access")
    if make_admin:
        _run(["usermod", "-aG", "sudo", username])
    else:
        _run(["usermod", "-rG", "sudo", username])
