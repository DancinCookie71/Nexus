"""File manager request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class FileEntry(BaseModel):
    name: str
    path: str
    type: str
    size: int
    modified_at: str
    mode: str
    owner: str
    group: str
    is_symlink: bool = False
    target: str | None = None


class FileListResponse(BaseModel):
    path: str
    entries: list[FileEntry]


class FileContentResponse(BaseModel):
    path: str
    content: str
    size: int
    mime_type: str


class FileWriteRequest(BaseModel):
    path: str
    content: str


class FileRenameRequest(BaseModel):
    source: str
    target: str


class FileCopyRequest(BaseModel):
    source: str
    target: str


class FileMkdirRequest(BaseModel):
    path: str


class FileDeleteRequest(BaseModel):
    path: str
    recursive: bool = False


class FileOperationResponse(BaseModel):
    success: bool
    message: str


class FileSearchResponse(BaseModel):
    query: str
    path: str
    include_hidden: bool
    total: int
    entries: list[FileEntry]


class FileExtractRequest(BaseModel):
    path: str = Field(..., min_length=1, max_length=4096)


class FileArchiveRequest(BaseModel):
    paths: list[str] = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=256)
