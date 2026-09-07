"""Service management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models import ServiceActionLog, SessionToken, User
from app.services.settings import get_setting
from app.schemas.services import (
    ServiceActionResponse,
    ServiceDetail as ServiceDetailSchema,
    ServiceListResponse,
    ServiceSummary as ServiceSummarySchema,
)
from app.services.systemd import (
    get_service_detail,
    list_services,
    perform_service_action,
    systemctl_available,
)

router = APIRouter(prefix="/services", tags=["services"])


def _log_action(
    db: Session,
    user: User,
    service_name: str,
    action: str,
    status: str,
    detail: str | None,
    ip_address: str | None,
) -> None:
    """Record a service action audit log entry."""
    log = ServiceActionLog(
        user_id=user.id,
        service_name=service_name,
        action=action,
        status=status,
        detail=detail,
        ip_address=ip_address,
    )
    db.add(log)
    db.commit()


def _normalize_service_name(service: str) -> str:
    """Ensure the service name ends with .service."""
    return service if service.endswith(".service") else f"{service}.service"


@router.get("", response_model=ServiceListResponse)
def list_services_endpoint(
    request: Request,
    show_system: bool = Query(False, description="Include system/internal services"),
    state_filter: str | None = Query(None, description="Filter by active state"),
    search: str | None = Query(None, description="Search by name or description"),
    current_user: User = Depends(get_current_user),
) -> ServiceListResponse:
    """Discover and list systemd services with optional filtering."""
    if not systemctl_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="systemctl is not available on this system",
        )

    raw_services = list_services(
        show_system=show_system,
        state_filter=state_filter,
        search=search,
    )
    services = [ServiceSummarySchema(**s.__dict__) for s in raw_services]
    return ServiceListResponse(
        services=services,
        total=len(services),
        show_system=show_system,
        state_filter=state_filter,
        search=search,
    )


@router.get("/{service}", response_model=ServiceDetailSchema)
def get_service_endpoint(
    service: str,
    current_user: User = Depends(get_current_user),
) -> ServiceDetailSchema:
    """Get detailed information about a single service."""
    if not systemctl_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="systemctl is not available on this system",
        )

    detail = get_service_detail(service)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Service not found",
        )
    return ServiceDetailSchema(**detail.__dict__)


@router.post("/{service}/{action}", response_model=ServiceActionResponse)
def service_action_endpoint(
    service: str,
    action: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    admin_session: SessionToken = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ServiceActionResponse:
    """Start, stop, restart, reload, enable, or disable a service."""
    if not systemctl_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="systemctl is not available on this system",
        )

    allowed_actions = {"start", "stop", "restart", "reload", "enable", "disable"}
    if action not in allowed_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be one of: start, stop, restart, reload, enable, disable",
        )

    service = _normalize_service_name(service)

    # Enforce the configured service allowlist.
    allowlist = get_setting(db, "service_allowlist", default=settings.service_allowlist)
    allowed_set = {item.strip() for item in allowlist.split(",") if item.strip()}
    allowed_set = {s if s.endswith(".service") else f"{s}.service" for s in allowed_set}
    if service not in allowed_set:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Service '{service}' is not in the allowed list",
        )

    client_ip = request.client.host if request.client else None

    try:
        success, message = perform_service_action(service, action)
        status_label = "success" if success else "error"
        _log_action(db, current_user, service, action, status_label, message, client_ip)

        new_detail = get_service_detail(service)
        return ServiceActionResponse(
            name=service,
            action=action,
            success=success,
            status=new_detail.status if new_detail else "unknown",
            message=message,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        _log_action(db, current_user, service, action, "error", str(exc), client_ip)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform service action",
        ) from exc
