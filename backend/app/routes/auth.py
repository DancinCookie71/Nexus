"""Authentication endpoints."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.auth import (
    authenticate_user,
    create_session,
    create_user,
    get_active_admin_session,
    get_or_create_unix_user,
    grant_admin,
    is_admin,
    is_real_unix_user,
    is_reserved_username,
    is_unix_sudoer,
    list_active_sessions,
    revoke_admin,
    revoke_session,
    revoke_session_by_id,
    verify_system_password,
)
from app.config import settings
from app.database import get_db
from app.dependencies import (
    admin_elevation_limiter,
    get_current_session,
    get_current_user,
    login_rate_limiter,
)
from app.models import SessionToken, User
from app.schemas.auth import (
    AdminElevateRequest,
    AdminStatusResponse,
    CreateFirstUserRequest,
    LoginRequest,
    LoginResponse,
    SessionInfo,
    UserResponse,
)
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _make_login_response(
    session_obj: SessionToken, plaintext_token: str, user: User
) -> LoginResponse:
    return LoginResponse(
        access_token=plaintext_token,
        token_type="bearer",
        expires_at=session_obj.expires_at,
        user=UserResponse.model_validate(user),
    )


def _set_session_cookie(request: Request, response: Response, token: str) -> None:
    """Set a secure, HTTP-only session cookie for the web client.

    The cookie is only marked Secure when the request was made over HTTPS,
    so local HTTP deployments still work.
    """
    secure = settings.is_production and request.url.scheme == "https"
    response.set_cookie(
        key="nexus_session",
        value=token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.session_lifetime_minutes * 60,
    )


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login(
    request: Request,
    response: Response,
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """Authenticate a user and return a bearer token (and session cookie)."""
    client_ip = request.client.host if request.client else None
    rate_key = client_ip or payload.username

    if not login_rate_limiter.is_allowed(rate_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )

    if is_reserved_username(payload.username):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = authenticate_user(db, payload.username, payload.password)
    if user is None and is_real_unix_user(payload.username):
        if verify_system_password(payload.username, payload.password):
            user = get_or_create_unix_user(db, payload.username)
    if user is None:
        login_rate_limiter.record_attempt(rate_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    login_rate_limiter.clear_attempts(rate_key)
    session_obj, token = create_session(
        db,
        user_id=user.id,
        user_agent=request.headers.get("user-agent"),
        ip_address=client_ip,
    )
    _set_session_cookie(request, response, token)
    return _make_login_response(session_obj, token, user)


@router.post("/logout", response_model=MessageResponse)
def logout(
    response: Response,
    session: SessionToken = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Revoke the current session and clear the cookie."""
    revoke_session(db, session)
    response.delete_cookie(key="nexus_session")
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return the currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.get("/sessions", response_model=list[SessionInfo])
def get_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SessionInfo]:
    """List active sessions for the current user."""
    sessions = list_active_sessions(db, current_user.id)
    return [SessionInfo.model_validate(s) for s in sessions]


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Revoke one of the current user's sessions."""
    if not revoke_session_by_id(db, current_user.id, session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return MessageResponse(message="Session revoked")


@router.post("/setup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_first_user(
    payload: CreateFirstUserRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Bootstrap the first admin user if no users exist."""
    existing = db.query(User).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Initial user already exists",
        )
    if is_reserved_username(payload.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is reserved",
        )
    user = create_user(db, payload.username, payload.password)
    return UserResponse.model_validate(user)


@router.post("/admin", response_model=AdminStatusResponse)
def elevate_admin(
    request: Request,
    payload: AdminElevateRequest,
    session: SessionToken = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> AdminStatusResponse:
    """Elevate the current session to admin mode after verifying a system password."""
    client_ip = request.client.host if request.client else None
    rate_key = client_ip or session.id

    if not admin_elevation_limiter.is_allowed(rate_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many admin elevation attempts. Please try again later.",
        )

    if not verify_system_password(payload.username, payload.password):
        admin_elevation_limiter.record_attempt(rate_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid system credentials",
        )

    if not is_unix_sudoer(payload.username):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin elevation requires a sudo-authorized system account",
        )

    admin_elevation_limiter.clear_attempts(rate_key)

    # Revoke any existing active grant first to reset the timer.
    revoke_admin(db, session)
    admin_session = grant_admin(db, session, ip_address=client_ip, sudo_username=payload.username)
    return AdminStatusResponse(
        is_admin=True,
        expires_at=admin_session.expires_at,
        username=payload.username,
        sudo_username=payload.username,
    )


@router.get("/admin", response_model=AdminStatusResponse)
def admin_status(
    session: SessionToken = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> AdminStatusResponse:
    """Return whether the current session has effective admin privileges.

    Includes implicit admin for UNIX-backed users in an admin group.
    """
    active = get_active_admin_session(db, session)
    implicit_user: Optional[str] = None
    if active is None:
        user = db.query(User).filter(User.id == session.user_id).first()
        if user is not None and user.auth_source == "unix" and is_unix_sudoer(user.username):
            implicit_user = user.username
    if active is not None:
        username = active.sudo_username
        expires_at = active.expires_at
    elif implicit_user is not None:
        username = implicit_user
        expires_at = None
    else:
        username = None
        expires_at = None
    return AdminStatusResponse(
        is_admin=active is not None or implicit_user is not None,
        expires_at=expires_at,
        username=username,
        sudo_username=username,
    )


@router.delete("/admin", response_model=MessageResponse)
def demote_admin(
    session: SessionToken = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Manually drop admin privileges for the current session."""
    revoked = revoke_admin(db, session)
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active admin privileges",
        )
    return MessageResponse(message="Admin privileges revoked")
