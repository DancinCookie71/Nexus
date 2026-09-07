"""System statistics and control endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user, require_admin
from app.models import SessionToken, User
from app.schemas.system import RebootResponse, SystemResponse
from app.services.system_stats import get_system_snapshot
from app.services.updates import reboot_system

router = APIRouter(prefix="/system", tags=["system"])


@router.get("", response_model=SystemResponse)
def system_stats(current_user: User = Depends(get_current_user)) -> SystemResponse:
    """Return current system statistics."""
    return get_system_snapshot()


@router.post("/reboot", response_model=RebootResponse)
def reboot(
    current_user: User = Depends(get_current_user),
    admin_session: SessionToken = Depends(require_admin),
) -> RebootResponse:
    """Reboot the system immediately (admin only)."""
    result = reboot_system()
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.message,
        )
    return RebootResponse(success=True, message=result.message)
