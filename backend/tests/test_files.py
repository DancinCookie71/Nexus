"""Tests for the file manager endpoints."""
from __future__ import annotations

import os
import tempfile

import pytest

from app.auth import create_user
from app.config import settings


@pytest.fixture
def files_user(db_session):
    return create_user(db_session, "filesadmin", "StrongPassword123!")


@pytest.fixture
def files_auth_client(client, db_session, files_user):
    from app.auth import create_session
    _, token = create_session(db_session, files_user.id)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def temp_files_root(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setattr(settings, "files_root", tmpdir)
        yield tmpdir


def test_list_files(files_auth_client, temp_files_root):
    os.makedirs(os.path.join(temp_files_root, "folder"))
    with open(os.path.join(temp_files_root, "file.txt"), "w") as f:
        f.write("hello")

    response = files_auth_client.get("/api/v1/files")
    assert response.status_code == 200
    data = response.json()
    assert data["path"] == ""
    names = {e["name"] for e in data["entries"]}
    assert "folder" in names
    assert "file.txt" in names


def test_read_file(files_auth_client, temp_files_root):
    with open(os.path.join(temp_files_root, "readme.md"), "w") as f:
        f.write("# Hello")

    response = files_auth_client.get("/api/v1/files/content?path=readme.md")
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "# Hello"


def test_download_file(files_auth_client, temp_files_root):
    with open(os.path.join(temp_files_root, "download.bin"), "wb") as f:
        f.write(b"binary data")

    response = files_auth_client.get("/api/v1/files/download?path=download.bin")
    assert response.status_code == 200
    assert response.content == b"binary data"


def test_upload_file(files_auth_client, temp_files_root):
    response = files_auth_client.post(
        "/api/v1/files/upload",
        data={"path": "uploaded.txt"},
        files={"file": ("uploaded.txt", b"uploaded content", "text/plain")},
    )
    assert response.status_code == 200
    with open(os.path.join(temp_files_root, "uploaded.txt")) as f:
        assert f.read() == "uploaded content"


def test_write_file(files_auth_client, temp_files_root):
    response = files_auth_client.post("/api/v1/files/content", json={
        "path": "new.txt",
        "content": "world",
    })
    assert response.status_code == 200
    with open(os.path.join(temp_files_root, "new.txt")) as f:
        assert f.read() == "world"


def test_create_directory(files_auth_client, temp_files_root):
    response = files_auth_client.post("/api/v1/files/mkdir", json={"path": "subdir"})
    assert response.status_code == 200
    assert os.path.isdir(os.path.join(temp_files_root, "subdir"))


def test_rename_file(files_auth_client, temp_files_root):
    with open(os.path.join(temp_files_root, "a.txt"), "w") as f:
        f.write("x")

    response = files_auth_client.post("/api/v1/files/rename", json={
        "source": "a.txt",
        "target": "b.txt",
    })
    assert response.status_code == 200
    assert os.path.isfile(os.path.join(temp_files_root, "b.txt"))


def test_delete_file(files_auth_client, temp_files_root):
    with open(os.path.join(temp_files_root, "delete.txt"), "w") as f:
        f.write("x")

    response = files_auth_client.delete("/api/v1/files?path=delete.txt")
    assert response.status_code == 200
    assert not os.path.exists(os.path.join(temp_files_root, "delete.txt"))


def test_copy_file(files_auth_client, temp_files_root):
    with open(os.path.join(temp_files_root, "a.txt"), "w") as f:
        f.write("copy me")

    response = files_auth_client.post("/api/v1/files/copy", json={
        "source": "a.txt",
        "target": "a_copy.txt",
    })
    assert response.status_code == 200
    assert os.path.isfile(os.path.join(temp_files_root, "a_copy.txt"))
    with open(os.path.join(temp_files_root, "a_copy.txt")) as f:
        assert f.read() == "copy me"


def test_search_files(files_auth_client, temp_files_root):
    os.makedirs(os.path.join(temp_files_root, "nested"))
    with open(os.path.join(temp_files_root, "alpha.txt"), "w") as f:
        f.write("1")
    with open(os.path.join(temp_files_root, "nested", "beta.txt"), "w") as f:
        f.write("2")

    response = files_auth_client.get("/api/v1/files/search?query=beta")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["entries"][0]["name"] == "beta.txt"


def test_path_traversal_blocked(files_auth_client, temp_files_root):
    response = files_auth_client.get("/api/v1/files?path=../etc")
    assert response.status_code == 403


def test_files_require_auth(client):
    response = client.get("/api/v1/files")
    assert response.status_code == 401
