"""Logs endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_current_user, require_admin
from app.models import SessionToken, User
from app.schemas.logs import LogEntry as LogEntrySchema, LogsResponse
from app.services.logs import journalctl_available, read_logs

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/{unit}", response_model=LogsResponse)
def get_logs(
    unit: str,
    limit: int = Query(200, ge=1, le=5000),
    since: str | None = Query(None, description="ISO 8601 or journalctl-style time"),
    until: str | None = Query(None, description="ISO 8601 or journalctl-style time"),
    priority: int | None = Query(None, ge=0, le=7),
    current_user: User = Depends(get_current_user),
    admin_session: SessionToken = Depends(require_admin),
) -> LogsResponse:
    """Read journal logs for a specific systemd unit."""
    if not journalctl_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="journalctl is not available on this system",
        )

    try:
        raw_entries = read_logs(unit, limit=limit, since=since, until=until, priority=priority)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    entries = [LogEntrySchema(**entry.__dict__) for entry in raw_entries]

    return LogsResponse(
        unit=unit,
        entries=entries,
        total=len(entries),
        limit=limit,
        since=since,
        until=until,
        priority=priority,
    )
