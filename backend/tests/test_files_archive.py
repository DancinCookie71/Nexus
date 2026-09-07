"""Tests for archive create/extract in the file manager."""
from __future__ import annotations

import io
import json
import subprocess
import sys
import tarfile
import zipfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest

from app.config import settings
from app.services.files import (
    FileManagerError,
    create_archive,
    extract_archive,
)


@contextmanager
def patch_login():
    with patch("app.routes.auth.is_real_unix_user", return_value=True), patch(
        "app.routes.auth.verify_system_password", return_value=True
    ):
        yield


@pytest.fixture
def archive_root(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "files_root", str(tmp_path))
    return tmp_path


def _make_tree(root: Path) -> None:
    (root / "docs").mkdir()
    (root / "docs" / "a.txt").write_text("alpha")
    (root / "docs" / "sub").mkdir()
    (root / "docs" / "sub" / "b.txt").write_text("beta")
    (root / "top.txt").write_text("top")


def test_create_and_extract_tar_gz_roundtrip(archive_root):
    _make_tree(archive_root)
    out = create_archive(["docs"], "docs.tar.gz")
    assert out == "docs.tar.gz"
    dest = extract_archive("docs.tar.gz")
    assert dest == "docs-2"
    assert (archive_root / "docs-2" / "docs" / "sub" / "b.txt").read_text() == "beta"


def test_create_and_extract_tgz_roundtrip(archive_root):
    _make_tree(archive_root)
    create_archive(["docs"], "backup.tgz")
    dest = extract_archive("backup.tgz")
    assert dest == "backup"
    assert (archive_root / "backup" / "docs" / "a.txt").read_text() == "alpha"


def test_create_and_extract_zip_roundtrip(archive_root):
    _make_tree(archive_root)
    create_archive(["docs"], "docs.zip")
    dest = extract_archive("docs.zip")
    assert dest == "docs-2"
    assert (archive_root / "docs-2" / "docs" / "a.txt").read_text() == "alpha"


def test_create_archive_rejects_unknown_extension(archive_root):
    _make_tree(archive_root)
    with pytest.raises(FileManagerError):
        create_archive(["docs"], "docs.rar")


def test_create_archive_rejects_traversal_name(archive_root):
    _make_tree(archive_root)
    with pytest.raises(FileManagerError):
        create_archive(["docs"], "../evil.tar.gz")
    assert not (archive_root.parent / "evil.tar.gz").exists()


def test_create_archive_rejects_existing_output(archive_root):
    _make_tree(archive_root)
    create_archive(["docs"], "docs.tar.gz")
    with pytest.raises(FileManagerError):
        create_archive(["docs"], "docs.tar.gz")


def test_extract_rejects_zip_path_traversal(archive_root):
    malicious = io.BytesIO()
    with zipfile.ZipFile(malicious, "w") as zf:
        zf.writestr("../evil.txt", "pwned")
    (archive_root / "bad.zip").write_bytes(malicious.getvalue())
    with pytest.raises(FileManagerError):
        extract_archive("bad.zip")
    assert not (archive_root / "evil.txt").exists()
    assert not (archive_root / "bad").exists()


def test_extract_rejects_zip_absolute_member(archive_root):
    malicious = io.BytesIO()
    with zipfile.ZipFile(malicious, "w") as zf:
        zf.writestr("/tmp/nexus-evil-marker", "pwned")
    (archive_root / "abs.zip").write_bytes(malicious.getvalue())
    with pytest.raises(FileManagerError):
        extract_archive("abs.zip")
    assert not Path("/tmp/nexus-evil-marker").exists()
    assert not (archive_root / "abs").exists()


def test_extract_rejects_tar_path_traversal(archive_root):
    p = archive_root / "evil.tar"
    with tarfile.open(p, "w") as tf:
        info = tarfile.TarInfo("../evil.txt")
        info.size = 4
        tf.addfile(info, io.BytesIO(b"pwn!"))
    with pytest.raises(FileManagerError):
        extract_archive("evil.tar")
    assert not (archive_root.parent / "evil.txt").exists()
    assert not (archive_root / "evil").exists()


def test_extract_rejects_unknown_type(archive_root):
    (archive_root / "thing.rar").write_bytes(b"not really")
    with pytest.raises(FileManagerError):
        extract_archive("thing.rar")


def test_extract_cleans_up_on_tar_error(archive_root):
    (archive_root / "broken.tar").write_bytes(b"garbage")
    with pytest.raises(FileManagerError):
        extract_archive("broken.tar")
    assert not (archive_root / "broken").exists()


def test_archive_endpoints_run_as_unix_user(client, db_session, monkeypatch):
    with patch_login():
        login = client.post(
            "/api/v1/auth/login",
            json={"username": "exampleuser", "password": "secret"},
        )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    calls = []

    def fake_worker(admin_user, func, *args, **kwargs):
        calls.append((admin_user, func))
        if func == "extract_archive":
            return {"dest": "out"}
        return {"archive": "out.tar.gz"}

    monkeypatch.setattr("app.services.files._run_worker", fake_worker)

    response = client.post("/api/v1/files/extract", headers=headers, json={"path": "a.zip"})
    assert response.status_code == 200

    response = client.post(
        "/api/v1/files/archive",
        headers=headers,
        json={"paths": ["docs"], "name": "d.tar.gz"},
    )
    assert response.status_code == 200
    assert calls == [
        ("exampleuser", "extract_archive"),
        ("exampleuser", "create_archive"),
    ]


def test_archive_endpoint_in_process_for_local_user(client, db_session, monkeypatch, tmp_path):
    from app.auth import create_user

    monkeypatch.setattr(settings, "files_root", str(tmp_path))
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.txt").write_text("alpha")
    create_user(db_session, "testadmin", "StrongPassword123!")

    def fail(*args, **kwargs):
        raise AssertionError("worker must not run for local users")

    monkeypatch.setattr("app.services.files._run_worker", fail)
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "testadmin", "password": "StrongPassword123!"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = client.post(
        "/api/v1/files/archive",
        headers=headers,
        json={"paths": ["docs"], "name": "d.tar.gz"},
    )
    assert response.status_code == 200
    assert (tmp_path / "d.tar.gz").exists()


def test_worker_create_archive_dispatch(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "files_root", str(tmp_path))
    _make_tree(tmp_path)
    worker = Path(__file__).resolve().parent.parent / "app" / "services" / "files_worker.py"
    command = {"func": "create_archive", "args": [["docs"], "d.tar.gz"], "files_root": str(tmp_path)}
    proc = subprocess.run(
        [sys.executable, str(worker)],
        input=json.dumps(command),
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(tmp_path),
        env={"PATH": "/usr/bin:/bin", "PYTHONIOENCODING": "utf-8"},
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["success"] is True
    assert (tmp_path / "d.tar.gz").exists()


def test_worker_extract_dispatch(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "files_root", str(tmp_path))
    _make_tree(tmp_path)
    create_archive(["docs"], "d.tar.gz")
    worker = Path(__file__).resolve().parent.parent / "app" / "services" / "files_worker.py"
    command = {"func": "extract_archive", "args": ["d.tar.gz"], "files_root": str(tmp_path)}
    proc = subprocess.run(
        [sys.executable, str(worker)],
        input=json.dumps(command),
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(tmp_path),
        env={"PATH": "/usr/bin:/bin", "PYTHONIOENCODING": "utf-8"},
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["success"] is True
    assert data["payload"]["dest"] == "d"
    assert (tmp_path / "d" / "docs" / "a.txt").read_text() == "alpha"
