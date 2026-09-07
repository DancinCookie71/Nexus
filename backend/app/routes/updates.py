"""System updates endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user, require_admin
from app.models import SessionToken, User
from app.schemas.updates import (
    ApplyUpdatesRequest,
    UpdateInfo,
    UpdateOperationResponse,
)
from app.services.updates import apply_updates, detect_updates, reboot_system

router = APIRouter(prefix="/updates", tags=["updates"])


@router.get("", response_model=UpdateInfo)
def get_updates(
    current_user: User = Depends(get_current_user),
    admin_session: SessionToken = Depends(require_admin),
) -> UpdateInfo:
    """Detect and return available system package updates (admin only)."""
    result = detect_updates()
    return UpdateInfo(
        supported=result.supported,
        package_manager=result.package_manager,
        update_count=result.update_count,
        packages=result.packages,
        error=result.error,
        last_checked=result.last_checked,
        reboot_required=result.reboot_required,
    )


@router.post("", response_model=UpdateOperationResponse)
def install_updates(
    request: ApplyUpdatesRequest,
    current_user: User = Depends(get_current_user),
    admin_session: SessionToken = Depends(require_admin),
) -> UpdateOperationResponse:
    """Apply all available system updates (admin only)."""
    result = apply_updates(reboot=request.reboot)
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.message,
        )
    return UpdateOperationResponse(
        success=True,
        message=result.message,
        reboot_scheduled=result.reboot_scheduled,
    )


@router.post("/reboot", response_model=UpdateOperationResponse)
def reboot(
    current_user: User = Depends(get_current_user),
    admin_session: SessionToken = Depends(require_admin),
) -> UpdateOperationResponse:
    """Reboot the system immediately (admin only)."""
    result = reboot_system()
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.message,
        )
    return UpdateOperationResponse(
        success=True,
        message=result.message,
        reboot_scheduled=True,
    )
