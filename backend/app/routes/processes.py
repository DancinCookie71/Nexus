"""Process listing and control endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_current_user, require_admin
from app.models import SessionToken, User
from app.schemas.common import MessageResponse
from app.schemas.processes import ProcessKillRequest, ProcessListResponse
from app.services.processes import ProcessError, kill_process, list_processes

router = APIRouter(prefix="/processes", tags=["processes"])


@router.get("", response_model=ProcessListResponse)
def get_processes(
    limit: int = Query(200, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
) -> ProcessListResponse:
    """Return a snapshot of running system processes."""
    return ProcessListResponse(**list_processes(limit))


@router.post("/{pid}/kill", response_model=MessageResponse)
def kill_process_endpoint(
    pid: int,
    request: ProcessKillRequest,
    current_user: User = Depends(get_current_user),
    admin_session: SessionToken = Depends(require_admin),
) -> MessageResponse:
    """Signal a process owned by the service user (admin only)."""
    try:
        kill_process(pid, request.signal)
    except ProcessError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return MessageResponse(message=f"Signal {request.signal} sent to process {pid}")
