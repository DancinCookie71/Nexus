"""Settings management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models import SessionToken, User
from app.schemas.common import MessageResponse
from app.schemas.settings import (
    SettingCreateRequest,
    SettingUpdateRequest,
    SettingValue,
    SettingsCategoryResponse,
)
from app.services.settings import (
    delete_setting,
    get_all_settings,
    get_setting,
    get_settings_by_category,
    set_setting,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsCategoryResponse)
def list_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SettingsCategoryResponse:
    """Return all settings grouped by category."""
    return SettingsCategoryResponse(categories=get_settings_by_category(db))


@router.get("/raw", response_model=list[SettingValue])
def list_settings_raw(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SettingValue]:
    """Return all settings as a flat list."""
    return [SettingValue.model_validate(s) for s in get_all_settings(db)]


@router.get("/{key}", response_model=SettingValue)
def get_setting_endpoint(
    key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SettingValue:
    """Return a single setting by key."""
    value = get_setting(db, key)
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found",
        )
    setting = set_setting(db, key, value)  # ensures model exists for response
    return SettingValue.model_validate(setting)


@router.put("/{key}", response_model=SettingValue)
def update_setting(
    key: str,
    payload: SettingUpdateRequest,
    admin_session: SessionToken = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SettingValue:
    """Update the value of an existing setting (admin required)."""
    existing = get_setting(db, key)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found",
        )
    setting = set_setting(db, key, payload.value)
    return SettingValue.model_validate(setting)


@router.post("", response_model=SettingValue, status_code=status.HTTP_201_CREATED)
def create_setting(
    payload: SettingCreateRequest,
    admin_session: SessionToken = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SettingValue:
    """Create or overwrite a setting (admin required)."""
    setting = set_setting(db, payload.key, payload.value, payload.category)
    return SettingValue.model_validate(setting)


@router.delete("/{key}", response_model=MessageResponse)
def remove_setting(
    key: str,
    admin_session: SessionToken = Depends(require_admin),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Delete a custom setting (admin required)."""
    if not delete_setting(db, key):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found",
        )
    return MessageResponse(message="Setting deleted")
