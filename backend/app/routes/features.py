"""Settings and feature-flag endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import settings
from app.dependencies import get_current_user
from app.models import User

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/features")
def get_features(current_user: User = Depends(get_current_user)) -> dict:
    """Return enabled feature flags for the frontend."""
    return {
        "terminal": settings.terminal_enabled,
        "service_management": True,
        "processes": True,
        "users": True,
        "logs": True,
    }
