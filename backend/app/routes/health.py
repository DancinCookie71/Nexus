"""Health monitoring endpoints."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status

from app import __version__
from app.auth import get_session_by_token, is_admin
from app.database import SessionLocal, get_db
from app.dependencies import get_current_session, get_current_user
from app.models import SessionToken, User
from app.schemas.health import HealthResponse
from app.services.health import HealthCollector, snapshot_to_dict
from sqlalchemy.orm import Session

router = APIRouter(prefix="/health", tags=["health"])


def _get_user_by_token(token: str) -> User | None:
    """Validate a bearer token and return the associated user."""
    db = SessionLocal()
    try:
        session_obj = get_session_by_token(db, token)
        if session_obj is None:
            return None
        return db.query(User).filter(User.id == session_obj.user_id).first()
    finally:
        db.close()


@router.get("")
def get_public_health() -> dict:
    """Return a simple public health status for load balancers and probes."""
    return {"status": "ok", "service": "nexus-api", "version": __version__}


@router.get("/live", response_model=HealthResponse)
def get_live_health(
    current_user: User = Depends(get_current_user),
    session: SessionToken = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> dict:
    """Return a current detailed snapshot of system health.

    SMART drive details are only included when the session has active admin
    privileges.
    """
    include_smart = is_admin(db, session)
    collector = HealthCollector()
    return snapshot_to_dict(collector.snapshot(include_smart=include_smart))


@router.websocket("/live/ws")
async def health_websocket(websocket: WebSocket, token: str | None = None) -> None:
    """Stream detailed health snapshots to the client every 2 seconds.

    The client must provide a valid session via the `token` query parameter or
    the `nexus_session` HTTP cookie.
    """
    auth_token = token or websocket.cookies.get("nexus_session")
    user = _get_user_by_token(auth_token) if auth_token else None
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Determine whether this session is in admin mode so SMART data can be
    # included in the stream.
    include_smart = False
    db = SessionLocal()
    try:
        session_obj = get_session_by_token(db, auth_token) if auth_token else None
        if session_obj is not None:
            include_smart = is_admin(db, session_obj)
    finally:
        db.close()

    await websocket.accept()
    collector = HealthCollector()
    try:
        while True:
            snapshot = await asyncio.to_thread(collector.snapshot, include_smart)
            await websocket.send_json(snapshot_to_dict(snapshot))
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
