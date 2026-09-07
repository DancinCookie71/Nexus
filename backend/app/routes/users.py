"""UNIX account management endpoints (admin only)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.dependencies import get_current_user, get_optional_admin_user, require_admin
from app.models import User
from app.schemas.common import MessageResponse
from app.schemas.users import (
    UnixUserAdminRequest,
    UnixUserInfo,
    UnixUserCreateRequest,
    UnixUserPasswordRequest,
)
from app.services.users import (
    UserManagementError,
    create_unix_user,
    delete_unix_user,
    list_unix_users,
    set_admin_membership,
    set_unix_password,
)

router = APIRouter(prefix="/users", tags=["users"])

_USERNAME_PATH = Path(..., pattern=r"^[a-z_][a-z0-9_-]{0,31}$")


def _handle_error(exc: UserManagementError) -> None:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=str(exc),
    ) from exc


@router.get("", response_model=list[UnixUserInfo])
def list_users(
    current_user: User = Depends(get_current_user),
    admin_session: User = Depends(require_admin),
) -> list[UnixUserInfo]:
    """List human local UNIX accounts (admin only)."""
    return [UnixUserInfo(**u) for u in list_unix_users()]


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def create_user_endpoint(
    payload: UnixUserCreateRequest,
    current_user: User = Depends(get_current_user),
    admin_session: User = Depends(require_admin),
    operator: str | None = Depends(get_optional_admin_user),
) -> MessageResponse:
    """Create a local UNIX account (admin only)."""
    try:
        create_unix_user(payload.username, payload.full_name, payload.password, payload.shell)
    except UserManagementError as exc:
        _handle_error(exc)
    return MessageResponse(message=f"User {payload.username} created")


@router.post("/{username}/password", response_model=MessageResponse)
def set_password_endpoint(
    payload: UnixUserPasswordRequest,
    username: str = _USERNAME_PATH,
    current_user: User = Depends(get_current_user),
    admin_session: User = Depends(require_admin),
) -> MessageResponse:
    """Set a local user's password (admin only)."""
    try:
        set_unix_password(username, payload.password)
    except UserManagementError as exc:
        _handle_error(exc)
    return MessageResponse(message=f"Password updated for {username}")


@router.post("/{username}/admin", response_model=MessageResponse)
def set_admin_endpoint(
    payload: UnixUserAdminRequest,
    username: str = _USERNAME_PATH,
    current_user: User = Depends(get_current_user),
    admin_session: User = Depends(require_admin),
    operator: str | None = Depends(get_optional_admin_user),
) -> MessageResponse:
    """Grant or revoke sudo-group membership (admin only)."""
    try:
        set_admin_membership(username, payload.admin, operator)
    except UserManagementError as exc:
        _handle_error(exc)
    state = "granted" if payload.admin else "revoked"
    return MessageResponse(message=f"Admin access {state} for {username}")


@router.delete("/{username}", response_model=MessageResponse)
def delete_user_endpoint(
    username: str = _USERNAME_PATH,
    current_user: User = Depends(get_current_user),
    admin_session: User = Depends(require_admin),
    operator: str | None = Depends(get_optional_admin_user),
) -> MessageResponse:
    """Delete a local UNIX account, keeping its home directory (admin only)."""
    try:
        delete_unix_user(username, operator)
    except UserManagementError as exc:
        _handle_error(exc)
    return MessageResponse(message=f"User {username} deleted")
