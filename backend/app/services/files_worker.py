"""Worker invoked by the file manager to run operations as another user.

This script is intended to be executed via sudo as the authenticated admin
user. It reads a JSON command from stdin, performs the requested file
operation, and prints a JSON result to stdout.
"""
from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

# Ensure the backend package root is importable.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_BACKEND_ROOT))

# The caller sets NEXUS_FILES_ROOT to the target user's home directory before
# importing the file manager services.
raw = sys.stdin.read()
command = json.loads(raw)
os.environ["NEXUS_FILES_ROOT"] = command.get("files_root", "/home/nexus")
# The worker runs with a minimal environment (no NEXUS_SECRET_KEY). It never
# signs tokens, so a placeholder satisfies the required Settings field.
os.environ.setdefault("NEXUS_SECRET_KEY", "files-worker-standalone")

from app.services.files import (  # noqa: E402
    FileContent,
    FileEntry,
    FileManagerError,
    copy_path,
    create_archive,
    create_directory,
    delete_path,
    extract_archive,
    get_entry,
    list_directory,
    read_file,
    rename_path,
    save_upload,
    search_files,
    write_file,
)


def _decode_arg(arg):
    if isinstance(arg, dict) and arg.get("__type__") == "bytes":
        return base64.b64decode(arg["data"])
    return arg


def _args():
    return [_decode_arg(a) for a in command["args"]]


MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024


def _download_file(relative_path: str) -> dict:
    """Read a file and return it base64-encoded for privileged downloads."""
    full_path = Path(relative_path)
    if not full_path.is_absolute():
        full_path = _root() / full_path
    resolved = full_path.resolve()
    try:
        resolved.relative_to(_root())
    except ValueError as exc:
        raise FileManagerError("Path is outside the allowed root directory") from exc
    if not resolved.is_file():
        raise FileManagerError("File not found")
    size = resolved.stat().st_size
    if size > MAX_DOWNLOAD_BYTES:
        raise FileManagerError(f"File is too large to download ({size} bytes)")
    data = resolved.read_bytes()
    return {"b64": base64.b64encode(data).decode(), "name": resolved.name}


def _root() -> Path:
    return Path(os.environ.get("NEXUS_FILES_ROOT", "/home/nexus")).resolve()


def _serialize_entry(entry: FileEntry) -> dict:
    return {
        "name": entry.name,
        "path": entry.path,
        "type": entry.type,
        "size": entry.size,
        "modified_at": entry.modified_at,
        "mode": entry.mode,
        "owner": entry.owner,
        "group": entry.group,
        "is_symlink": entry.is_symlink,
        "target": entry.target,
    }


def _serialize_content(content: FileContent) -> dict:
    return {
        "path": content.path,
        "content": content.content,
        "size": content.size,
        "mime_type": content.mime_type,
    }


def main() -> None:
    func_name = command["func"]
    try:
        if func_name == "list_directory":
            path, entries = list_directory(*_args())
            payload = {"path": path, "entries": [_serialize_entry(e) for e in entries]}
        elif func_name == "read_file":
            payload = _serialize_content(read_file(*_args()))
        elif func_name == "write_file":
            write_file(*_args())
            payload = None
        elif func_name == "create_directory":
            create_directory(*_args())
            payload = None
        elif func_name == "delete_path":
            delete_path(*_args())
            payload = None
        elif func_name == "rename_path":
            rename_path(*_args())
            payload = None
        elif func_name == "copy_path":
            copy_path(*_args())
            payload = None
        elif func_name == "save_upload":
            save_upload(*_args())
            payload = None
        elif func_name == "search_files":
            entries = search_files(*_args())
            payload = {"entries": [_serialize_entry(e) for e in entries]}
        elif func_name == "get_entry":
            payload = _serialize_entry(get_entry(*_args()))
        elif func_name == "download_file":
            payload = _download_file(*_args())
        elif func_name == "extract_archive":
            payload = {"dest": extract_archive(*_args())}
        elif func_name == "create_archive":
            payload = {"archive": create_archive(*_args())}
        else:
            raise FileManagerError(f"Unknown worker function: {func_name}")
        print(json.dumps({"success": True, "payload": payload}))
    except FileManagerError as exc:
        print(json.dumps({"success": False, "error": str(exc)}))
    except Exception as exc:
        print(json.dumps({"success": False, "error": f"Worker error: {exc}"}))


if __name__ == "__main__":
    main()
