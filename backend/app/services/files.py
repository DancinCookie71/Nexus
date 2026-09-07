"""Safe file manager operations constrained to a configurable root.

Operations can optionally run as an authenticated admin user via a worker
subprocess executed through sudo.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.config import settings


class FileManagerError(Exception):
    """Raised for filesystem errors or unsafe paths."""


@dataclass
class FileEntry:
    name: str
    path: str
    type: str  # file, directory, symlink
    size: int
    modified_at: str
    mode: str
    owner: str
    group: str
    is_symlink: bool = False
    target: Optional[str] = None


@dataclass
class FileContent:
    path: str
    content: str
    size: int
    mime_type: str


_WORKER_PATH = Path(__file__).resolve().with_name("files_worker.py")


def _root_path() -> Path:
    return Path(settings.files_root).resolve()


def _home_for_user(username: str) -> str:
    """Return the user's real home directory, falling back to /home/{username}."""
    try:
        import pwd

        return pwd.getpwnam(username).pw_dir
    except Exception:
        return f"/home/{username}"


def _encode_arg(arg):
    if isinstance(arg, bytes):
        return {"__type__": "bytes", "data": base64.b64encode(arg).decode()}
    return arg


def _run_worker(admin_user: str, func: str, *args) -> dict:
    """Run a file operation as admin_user via the worker subprocess."""
    command = {
        "func": func,
        "args": [_encode_arg(a) for a in args],
        "files_root": _home_for_user(admin_user),
    }
    cwd = _home_for_user(admin_user)
    # Run the worker directly without a shell to avoid interpolation issues.
    # Pass only the minimal environment the worker needs.
    proc = subprocess.run(
        ["sudo", "-n", "-u", admin_user, "-H", sys.executable, str(_WORKER_PATH)],
        input=json.dumps(command),
        capture_output=True,
        text=True,
        timeout=120,
        cwd=cwd,
        env={
            "HOME": cwd,
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONIOENCODING": "utf-8",
        },
    )
    if proc.returncode != 0:
        raise FileManagerError(
            f"Privileged operation failed: {proc.stderr.strip() or proc.stdout.strip()}"
        )
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise FileManagerError(f"Privileged operation returned invalid output: {proc.stdout}") from exc
    if not data.get("success"):
        raise FileManagerError(data.get("error", "Privileged operation failed"))
    return data.get("payload")


def _resolve_safe(relative_path: str) -> Path:
    """Resolve a path relative to the files root and prevent traversal."""
    root = _root_path()
    # Normalize the input: strip leading slashes and collapse .
    cleaned = os.path.normpath(relative_path.strip("/"))
    if cleaned == ".":
        cleaned = ""
    resolved = (root / cleaned).resolve()
    # Ensure resolved path is under root.
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise FileManagerError("Path is outside the allowed root directory") from exc
    return resolved


def _stat_owner_group(st: os.stat_result) -> tuple[str, str]:
    try:
        owner = str(st.st_uid)
        group = str(st.st_gid)
        import pwd
        import grp
        owner = pwd.getpwuid(st.st_uid).pw_name
        group = grp.getgrgid(st.st_gid).gr_name
    except Exception:
        pass
    return owner, group


def _mode_str(st: os.stat_result) -> str:
    return stat.filemode(st.st_mode)


def _format_time(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _entry_from_path(full_path: Path, relative_path: str) -> FileEntry:
    st = full_path.lstat()
    is_symlink = stat.S_ISLNK(st.st_mode)
    target = None
    if is_symlink:
        try:
            target = os.readlink(full_path)
            # Resolve target type for display.
            st = full_path.stat()
        except Exception:
            pass

    if stat.S_ISDIR(st.st_mode):
        entry_type = "directory"
    else:
        entry_type = "file"

    owner, group = _stat_owner_group(st)
    return FileEntry(
        name=full_path.name,
        path=relative_path,
        type=entry_type,
        size=st.st_size,
        modified_at=_format_time(st.st_mtime),
        mode=_mode_str(st),
        owner=owner,
        group=group,
        is_symlink=is_symlink,
        target=target,
    )


def list_directory(relative_path: str = "", admin_user: Optional[str] = None) -> tuple[str, list[FileEntry]]:
    """List the contents of a directory under the files root."""
    if admin_user:
        payload = _run_worker(admin_user, "list_directory", relative_path)
        return payload["path"], [FileEntry(**e) for e in payload["entries"]]

    full_path = _resolve_safe(relative_path)
    if not full_path.is_dir():
        raise FileManagerError("Not a directory")

    root = _root_path()
    entries: list[FileEntry] = []
    try:
        for item in sorted(full_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            rel = str(item.relative_to(root))
            entries.append(_entry_from_path(item, rel))
    except PermissionError as exc:
        raise FileManagerError("Permission denied") from exc
    relative = str(full_path.relative_to(root))
    return "" if relative == "." else relative, entries


def _guess_mime_type(path: Path) -> str:
    """Guess MIME type from file extension."""
    import mimetypes

    mime, _ = mimetypes.guess_type(str(path))
    return mime or "text/plain"


def _is_binary(path: Path, sample_size: int = 8192) -> bool:
    """Detect whether a file is binary by sampling its first bytes."""
    try:
        with path.open("rb") as fh:
            sample = fh.read(sample_size)
    except Exception:
        return True
    if not sample:
        return False
    # Null bytes are a strong signal of binary content.
    if b"\x00" in sample:
        return True
    # If the sample cannot be decoded as UTF-8, treat as binary.
    try:
        sample.decode("utf-8")
        return False
    except UnicodeDecodeError:
        return True


def read_file(relative_path: str, max_bytes: int = 1024 * 1024, admin_user: Optional[str] = None) -> FileContent:
    """Read a text file and return its contents."""
    if admin_user:
        payload = _run_worker(admin_user, "read_file", relative_path, max_bytes)
        return FileContent(**payload)

    full_path = _resolve_safe(relative_path)
    if full_path.is_dir():
        raise FileManagerError("Cannot read a directory")
    if not full_path.is_file():
        raise FileManagerError("File not found")

    size = full_path.stat().st_size
    if size > max_bytes:
        raise FileManagerError(f"File is too large to display ({size} bytes)")

    mime = _guess_mime_type(full_path)
    if _is_binary(full_path):
        mime = "application/octet-stream"
        content = "[Binary file cannot be edited in the browser]"
    else:
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            raise FileManagerError(f"Failed to read file: {exc}") from exc

    return FileContent(
        path=relative_path,
        content=content,
        size=size,
        mime_type=mime,
    )


def resolve_file(relative_path: str, admin_user: Optional[str] = None) -> Path:
    """Resolve a regular file for a controlled download."""
    if admin_user:
        raise FileManagerError("Downloads in admin context should use download endpoint")
    full_path = _resolve_safe(relative_path)
    if not full_path.is_file():
        raise FileManagerError("File not found")
    return full_path


def write_file(relative_path: str, content: str, admin_user: Optional[str] = None) -> None:
    """Write text content to a file under the files root."""
    if admin_user:
        _run_worker(admin_user, "write_file", relative_path, content)
        return
    full_path = _resolve_safe(relative_path)
    if full_path.is_dir():
        raise FileManagerError("Cannot write to a directory")
    try:
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
    except Exception as exc:
        raise FileManagerError(f"Failed to write file: {exc}") from exc


def create_directory(relative_path: str, admin_user: Optional[str] = None) -> None:
    """Create a directory under the files root."""
    if admin_user:
        _run_worker(admin_user, "create_directory", relative_path)
        return
    full_path = _resolve_safe(relative_path)
    try:
        full_path.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        raise FileManagerError(f"Failed to create directory: {exc}") from exc


def delete_path(relative_path: str, recursive: bool = False, admin_user: Optional[str] = None) -> None:
    """Delete a file or directory under the files root."""
    if admin_user:
        _run_worker(admin_user, "delete_path", relative_path, recursive)
        return
    full_path = _resolve_safe(relative_path)
    if full_path == _root_path():
        raise FileManagerError("Cannot delete the root directory")
    try:
        if full_path.is_dir():
            if recursive:
                shutil.rmtree(full_path)
            else:
                full_path.rmdir()
        else:
            full_path.unlink()
    except Exception as exc:
        raise FileManagerError(f"Failed to delete: {exc}") from exc


def rename_path(source: str, target: str, admin_user: Optional[str] = None) -> None:
    """Rename or move a file/directory under the files root."""
    if admin_user:
        _run_worker(admin_user, "rename_path", source, target)
        return
    src_path = _resolve_safe(source)
    dst_path = _resolve_safe(target)
    try:
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        src_path.rename(dst_path)
    except Exception as exc:
        raise FileManagerError(f"Failed to rename: {exc}") from exc


def save_upload(relative_path: str, data: bytes, admin_user: Optional[str] = None) -> None:
    """Save uploaded binary data to a file under the files root."""
    if admin_user:
        _run_worker(admin_user, "save_upload", relative_path, data)
        return
    full_path = _resolve_safe(relative_path)
    if full_path.is_dir():
        raise FileManagerError("Cannot overwrite a directory")
    try:
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)
    except Exception as exc:
        raise FileManagerError(f"Failed to save upload: {exc}") from exc


def copy_path(source: str, target: str, admin_user: Optional[str] = None) -> None:
    """Copy a file or directory under the files root."""
    if admin_user:
        _run_worker(admin_user, "copy_path", source, target)
        return
    src_path = _resolve_safe(source)
    dst_path = _resolve_safe(target)
    if src_path == _root_path():
        raise FileManagerError("Cannot copy the root directory")
    if dst_path == _root_path():
        raise FileManagerError("Cannot copy over the root directory")
    if dst_path.exists() and dst_path.is_dir():
        if src_path.is_dir():
            raise FileManagerError(
                "Cannot copy a directory into an existing directory"
            )
        # If target is an existing directory, copy source inside it.
        dst_path = dst_path / src_path.name
    try:
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        if src_path.is_dir():
            shutil.copytree(src_path, dst_path)
        else:
            shutil.copy2(src_path, dst_path)
    except Exception as exc:
        raise FileManagerError(f"Failed to copy: {exc}") from exc


def get_entry(relative_path: str, admin_user: Optional[str] = None) -> FileEntry:
    """Return metadata for a single file or directory."""
    if admin_user:
        payload = _run_worker(admin_user, "get_entry", relative_path)
        return FileEntry(**payload)
    full_path = _resolve_safe(relative_path)
    rel = str(full_path.relative_to(_root_path()))
    return _entry_from_path(full_path, rel)


def search_files(
    query: str,
    relative_path: str = "",
    include_hidden: bool = False,
    limit: int = 500,
    admin_user: Optional[str] = None,
) -> list[FileEntry]:
    """Search for files and folders by name under the given relative path."""
    if admin_user:
        payload = _run_worker(admin_user, "search_files", query, relative_path, include_hidden, limit)
        return [FileEntry(**e) for e in payload["entries"]]
    base = _resolve_safe(relative_path)
    if not base.is_dir():
        raise FileManagerError("Not a directory")
    root = _root_path()
    results: list[FileEntry] = []
    q = query.lower()
    try:
        for path in base.rglob("*"):
            # Do not follow symlinks during search to avoid escaping the root.
            if path.is_symlink():
                continue
            name = path.name
            if not include_hidden and name.startswith("."):
                continue
            if q in name.lower():
                rel = str(path.relative_to(root))
                results.append(_entry_from_path(path, rel))
                if len(results) >= limit:
                    break
    except PermissionError as exc:
        raise FileManagerError("Permission denied") from exc
    return results


def download_file_path(relative_path: str, admin_user: Optional[str] = None) -> Path:
    """Resolve a file for download, optionally as another user.

    Downloads in admin context are streamed through the privileged worker so
    the file permissions of the target user are respected, and the temporary
    file keeps the original filename.
    """
    if admin_user:
        payload = _run_worker(admin_user, "download_file", relative_path)
        data = base64.b64decode(payload["b64"])
        # Keep the original filename in the temporary file so downloads are
        # named correctly. Only the basename is used to prevent traversal.
        safe_name = os.path.basename(payload["name"]) or "download"
        tmp_path = Path("/tmp") / f"nexus-download-{os.urandom(8).hex()}-{safe_name}"
        tmp_path.write_bytes(data)
        tmp_path.chmod(0o600)
        return tmp_path
    return resolve_file(relative_path)


MAX_ARCHIVE_BYTES = 1024 * 1024 * 1024


def _safe_archive_member_path(dest: Path, member_name: str) -> Path:
    """Resolve an archive member path, rejecting traversal outside dest."""
    if member_name.startswith("/") or ".." in Path(member_name).parts:
        raise FileManagerError("Archive contains an unsafe path")
    candidate = (dest / member_name).resolve()
    if candidate != dest and dest not in candidate.parents:
        raise FileManagerError("Archive contains an unsafe path")
    return candidate


def _archive_dest_for(src: Path) -> Path:
    name = src.name.lower()
    if name.endswith(".tar.gz"):
        return src.parent / src.name[:-7]
    if name.endswith(".tgz"):
        return src.parent / src.name[:-4]
    if name.endswith(".tar"):
        return src.parent / src.name[:-4]
    if name.endswith(".zip"):
        return src.parent / src.name[:-4]
    raise FileManagerError("Unsupported archive type")


def _unique_destination(dest: Path) -> Path:
    """Return dest, or dest-2, dest-3, ... if the path already exists."""
    if not dest.exists():
        return dest
    for i in range(2, 1000):
        candidate = dest.with_name(f"{dest.name}-{i}")
        if not candidate.exists():
            return candidate
    raise FileManagerError("No free destination folder name")


def extract_archive(relative_path: str, admin_user: Optional[str] = None) -> str:
    """Extract a tar/tar.gz/tgz/zip archive into a new sibling folder."""
    if admin_user:
        payload = _run_worker(admin_user, "extract_archive", relative_path)
        return payload["dest"]

    src = _resolve_safe(relative_path)
    if not src.is_file():
        raise FileManagerError("File not found")
    name = src.name.lower()
    if name.endswith((".tar.gz", ".tgz")):
        mode = "r:gz"
    elif name.endswith(".tar"):
        mode = "r:"
    elif name.endswith(".zip"):
        mode = "zip"
    else:
        raise FileManagerError("Unsupported archive type")

    dest = _archive_dest_for(src).resolve()
    if not dest.name:
        raise FileManagerError("Invalid archive name")
    dest = _unique_destination(dest)

    dest.mkdir(parents=True)
    try:
        if mode == "zip":
            import zipfile

            with zipfile.ZipFile(src) as zf:
                total = sum(i.file_size for i in zf.infolist())
                if total > MAX_ARCHIVE_BYTES:
                    raise FileManagerError(
                        f"Archive is too large to extract ({total} bytes)"
                    )
                for member in zf.namelist():
                    target = _safe_archive_member_path(dest, member)
                    if member.endswith("/"):
                        target.mkdir(parents=True, exist_ok=True)
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as fh, target.open("wb") as out:
                        shutil.copyfileobj(fh, out)
        else:
            import tarfile

            with tarfile.open(src, mode) as tf:
                tf.extractall(dest, filter="data")
    except FileManagerError:
        shutil.rmtree(dest, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(dest, ignore_errors=True)
        raise FileManagerError(f"Failed to extract archive: {exc}") from exc
    return str(dest.relative_to(_root_path()))


def create_archive(
    paths: list[str],
    archive_name: str,
    admin_user: Optional[str] = None,
) -> str:
    """Create a .tar.gz, .tgz or .zip archive from paths under the files root."""
    if admin_user:
        payload = _run_worker(admin_user, "create_archive", paths, archive_name)
        return payload["archive"]

    name = archive_name.strip()
    lower = name.lower()
    if lower.endswith(".zip"):
        fmt = "zip"
    elif lower.endswith((".tar.gz", ".tgz")):
        fmt = "tar.gz"
    else:
        raise FileManagerError("Archive name must end with .tar.gz, .tgz, or .zip")
    if not name or "/" in name or name.startswith("."):
        raise FileManagerError("Invalid archive name")

    root = _root_path()
    sources = [_resolve_safe(p) for p in paths]
    if any(s == root for s in sources):
        raise FileManagerError("Cannot archive the root directory")

    out = (root / name).resolve()
    if out != root and root not in out.parents:
        raise FileManagerError("Invalid archive path")
    if out.exists():
        raise FileManagerError("A file with that name already exists")

    try:
        if fmt == "zip":
            import zipfile

            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
                for s in sources:
                    if s.is_dir():
                        for f in sorted(s.rglob("*")):
                            if f.is_file() and not f.is_symlink():
                                zf.write(f, str(f.relative_to(root)))
                    elif s.is_file():
                        zf.write(s, str(s.relative_to(root)))
        else:
            import tarfile

            with tarfile.open(out, "w:gz") as tf:
                for s in sources:
                    tf.add(s, arcname=str(s.relative_to(root)), recursive=True)
    except Exception as exc:
        out.unlink(missing_ok=True)
        raise FileManagerError(f"Failed to create archive: {exc}") from exc
    return str(out.relative_to(root))
