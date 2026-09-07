"""Storage / drive management endpoints."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user, require_admin
from app.models import SessionToken, User
from app.schemas.storage import DriveDetail, DriveListResponse, DriveSummary
from app.services.storage import drive_to_dict, examine_drive, list_drives

router = APIRouter(prefix="/storage", tags=["storage"])

_DEVICE_PATTERN = re.compile(r"^/dev/[a-zA-Z0-9_-]+$")


def _summarize_drive(info: dict) -> DriveSummary:
    return DriveSummary(
        device=info["device"],
        model=info["model"],
        serial=info["serial"],
        size_human=info["size_human"],
        is_ssd=info["is_ssd"],
        smart_supported=info["smart_supported"],
        smart_enabled=info["smart_enabled"],
        smart_status=info["smart_status"],
        temperature_c=info["temperature_c"],
        power_on_hours=info["power_on_hours"],
        status=info["status"],
    )


@router.get("/drives", response_model=DriveListResponse)
def list_drives_endpoint(
    current_user: User = Depends(get_current_user),
    admin_session: SessionToken = Depends(require_admin),
) -> DriveListResponse:
    """List physical drives with basic SMART status."""
    drives = [drive_to_dict(d) for d in list_drives()]
    return DriveListResponse(
        drives=[_summarize_drive(d) for d in drives],
        total=len(drives),
    )


@router.get("/drives/{device:path}", response_model=DriveDetail)
def examine_drive_endpoint(
    device: str,
    current_user: User = Depends(get_current_user),
    admin_session: SessionToken = Depends(require_admin),
) -> DriveDetail:
    """Return detailed SMART information for a single drive."""
    if not _DEVICE_PATTERN.match(device):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid device path",
        )

    info = drive_to_dict(examine_drive(device))
    return DriveDetail(**info)
