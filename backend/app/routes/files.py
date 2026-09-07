"""File manager endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, get_optional_admin_user, require_admin_if_files_writes_locked
from app.models import SessionToken, User
from app.schemas.files import (
    FileArchiveRequest,
    FileContentResponse,
    FileCopyRequest,
    FileEntry,
    FileExtractRequest,
    FileListResponse,
    FileMkdirRequest,
    FileOperationResponse,
    FileRenameRequest,
    FileSearchResponse,
    FileWriteRequest,
)
from app.services.files import (
    FileManagerError,
    copy_path,
    create_archive,
    create_directory,
    delete_path,
    download_file_path,
    extract_archive,
    get_entry,
    list_directory,
    read_file,
    rename_path,
    save_upload,
    search_files,
    write_file,
)

router = APIRouter(prefix="/files", tags=["files"])

MAX_READ_BYTES = 2 * 1024 * 1024
MAX_WRITE_BYTES = 2 * 1024 * 1024
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


def _handle_error(exc: FileManagerError) -> None:
    """Map FileManagerError to an appropriate HTTP status code."""
    message = str(exc).lower()
    if "not found" in message or "no such file" in message:
        code = status.HTTP_404_NOT_FOUND
    elif "permission denied" in message or "outside the allowed root" in message:
        code = status.HTTP_403_FORBIDDEN
    elif "too large" in message:
        code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    elif "already exists" in message or "file exists" in message:
        code = status.HTTP_409_CONFLICT
    else:
        code = status.HTTP_400_BAD_REQUEST
    raise HTTPException(
        status_code=code,
        detail=str(exc),
    ) from exc


@router.get("", response_model=FileListResponse)
def list_files(
    path: str = Query("", max_length=4096, description="Relative path under the files root"),
    current_user: User = Depends(get_current_user),
    admin_user: str | None = Depends(get_optional_admin_user),
) -> FileListResponse:
    """List files and directories under the configured files root."""
    try:
        current_path, entries = list_directory(path, admin_user=admin_user)
    except FileManagerError as exc:
        _handle_error(exc)
    return FileListResponse(
        path=current_path,
        entries=[
            {
                "name": e.name,
                "path": e.path,
                "type": e.type,
                "size": e.size,
                "modified_at": e.modified_at,
                "mode": e.mode,
                "owner": e.owner,
                "group": e.group,
                "is_symlink": e.is_symlink,
                "target": e.target,
            }
            for e in entries
        ],
    )


@router.get("/content", response_model=FileContentResponse)
def get_file_content(
    path: str = Query(..., max_length=4096, description="Relative path to the file"),
    current_user: User = Depends(get_current_user),
    admin_user: str | None = Depends(get_optional_admin_user),
) -> FileContentResponse:
    """Read the contents of a text file."""
    try:
        content = read_file(path, max_bytes=MAX_READ_BYTES, admin_user=admin_user)
    except FileManagerError as exc:
        _handle_error(exc)
    return FileContentResponse(
        path=content.path,
        content=content.content,
        size=content.size,
        mime_type=content.mime_type,
    )


@router.post("/content", response_model=FileOperationResponse)
def update_file_content(
    request: FileWriteRequest,
    current_user: User = Depends(get_current_user),
    admin_session: SessionToken = Depends(require_admin_if_files_writes_locked),
    admin_user: str | None = Depends(get_optional_admin_user),
) -> FileOperationResponse:
    """Write text content to a file."""
    if len(request.content.encode("utf-8")) > MAX_WRITE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Edited files are limited to 2 MiB",
        )
    try:
        write_file(request.path, request.content, admin_user=admin_user)
    except FileManagerError as exc:
        _handle_error(exc)
    return FileOperationResponse(success=True, message="File saved")


@router.post("/mkdir", response_model=FileOperationResponse)
def make_directory(
    request: FileMkdirRequest,
    current_user: User = Depends(get_current_user),
    admin_session: SessionToken = Depends(require_admin_if_files_writes_locked),
    admin_user: str | None = Depends(get_optional_admin_user),
) -> FileOperationResponse:
    """Create a new directory."""
    try:
        create_directory(request.path, admin_user=admin_user)
    except FileManagerError as exc:
        _handle_error(exc)
    return FileOperationResponse(success=True, message="Directory created")


@router.post("/rename", response_model=FileOperationResponse)
def rename_file(
    request: FileRenameRequest,
    current_user: User = Depends(get_current_user),
    admin_session: SessionToken = Depends(require_admin_if_files_writes_locked),
    admin_user: str | None = Depends(get_optional_admin_user),
) -> FileOperationResponse:
    """Rename or move a file or directory."""
    try:
        rename_path(request.source, request.target, admin_user=admin_user)
    except FileManagerError as exc:
        _handle_error(exc)
    return FileOperationResponse(success=True, message="Renamed successfully")


@router.get("/download")
def download_file(
    path: str = Query(..., max_length=4096, description="Relative path to the file"),
    current_user: User = Depends(get_current_user),
    admin_user: str | None = Depends(get_optional_admin_user),
) -> FileResponse:
    """Download a regular file under the configured files root."""
    try:
        full_path = download_file_path(path, admin_user=admin_user)
    except FileManagerError as exc:
        _handle_error(exc)
    response = FileResponse(full_path, filename=full_path.name)
    # Clean up temporary privileged-download files after serving.
    if admin_user and str(full_path).startswith("/tmp/"):
        from starlette.background import BackgroundTask
        import os as _os
        response.background = BackgroundTask(lambda p: _os.unlink(p), str(full_path))
    return response


@router.post("/copy", response_model=FileOperationResponse)
def copy_file(
    request: FileCopyRequest,
    current_user: User = Depends(get_current_user),
    admin_session: SessionToken = Depends(require_admin_if_files_writes_locked),
    admin_user: str | None = Depends(get_optional_admin_user),
) -> FileOperationResponse:
    """Copy a file or directory under the files root."""
    try:
        copy_path(request.source, request.target, admin_user=admin_user)
    except FileManagerError as exc:
        _handle_error(exc)
    return FileOperationResponse(success=True, message="Copied successfully")


@router.get("/search", response_model=FileSearchResponse)
def search_files_endpoint(
    query: str = Query(..., min_length=1, max_length=256, description="Search term"),
    path: str = Query("", max_length=4096, description="Relative path to search under"),
    show_hidden: bool = Query(False, description="Include hidden files"),
    current_user: User = Depends(get_current_user),
    admin_user: str | None = Depends(get_optional_admin_user),
) -> FileSearchResponse:
    """Search for files and folders by name under the configured root."""
    try:
        results = search_files(query, path, include_hidden=show_hidden, admin_user=admin_user)
    except FileManagerError as exc:
        _handle_error(exc)
    return FileSearchResponse(
        query=query,
        path=path,
        include_hidden=show_hidden,
        total=len(results),
        entries=[FileEntry.model_validate(e.__dict__) for e in results],
    )


@router.get("/info", response_model=FileEntry)
def file_info(
    path: str = Query(..., max_length=4096, description="Relative path to the file or directory"),
    current_user: User = Depends(get_current_user),
    admin_user: str | None = Depends(get_optional_admin_user),
) -> FileEntry:
    """Return metadata for a single file or directory."""
    try:
        entry = get_entry(path, admin_user=admin_user)
    except FileManagerError as exc:
        _handle_error(exc)
    return FileEntry.model_validate(entry.__dict__)


@router.delete("", response_model=FileOperationResponse)
def delete_file(
    path: str = Query(..., max_length=4096, description="Relative path to delete"),
    recursive: bool = Query(False, description="Delete directories recursively"),
    current_user: User = Depends(get_current_user),
    admin_session: SessionToken = Depends(require_admin_if_files_writes_locked),
    admin_user: str | None = Depends(get_optional_admin_user),
) -> FileOperationResponse:
    """Delete a file or directory."""
    try:
        delete_path(path, recursive=recursive, admin_user=admin_user)
    except FileManagerError as exc:
        _handle_error(exc)
    return FileOperationResponse(success=True, message="Deleted successfully")


@router.post("/extract", response_model=FileOperationResponse)
def extract_archive_endpoint(
    request: FileExtractRequest,
    current_user: User = Depends(get_current_user),
    admin_session: SessionToken = Depends(require_admin_if_files_writes_locked),
    admin_user: str | None = Depends(get_optional_admin_user),
) -> FileOperationResponse:
    """Extract a tar/tar.gz/zip archive into a new sibling folder."""
    try:
        dest = extract_archive(request.path, admin_user=admin_user)
    except FileManagerError as exc:
        _handle_error(exc)
    return FileOperationResponse(success=True, message=f"Extracted to {dest}")


@router.post("/archive", response_model=FileOperationResponse)
def create_archive_endpoint(
    request: FileArchiveRequest,
    current_user: User = Depends(get_current_user),
    admin_session: SessionToken = Depends(require_admin_if_files_writes_locked),
    admin_user: str | None = Depends(get_optional_admin_user),
) -> FileOperationResponse:
    """Create a .tar.gz/.tgz/.zip archive from paths under the files root."""
    try:
        archive = create_archive(request.paths, request.name, admin_user=admin_user)
    except FileManagerError as exc:
        _handle_error(exc)
    return FileOperationResponse(success=True, message=f"Created {archive}")


@router.post("/upload", response_model=FileOperationResponse)
def upload_file(
    path: str = Form(..., max_length=4096, description="Relative path where the file should be saved"),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    admin_session: SessionToken = Depends(require_admin_if_files_writes_locked),
    admin_user: str | None = Depends(get_optional_admin_user),
) -> FileOperationResponse:
    """Upload a file to the specified relative path."""
    try:
        data = file.file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Uploads are limited to 50 MiB",
            )
        save_upload(path, data, admin_user=admin_user)
    except FileManagerError as exc:
        _handle_error(exc)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload failed",
        ) from exc
    return FileOperationResponse(success=True, message="File uploaded")
