"""Service management request/response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import UTCDateTime


class ServiceSummary(BaseModel):
    """Brief service information for list views."""

    name: str
    description: str
    load_state: str
    active_state: str
    sub_state: str
    unit_file_state: str
    main_pid: int = 0
    memory_current: Optional[int] = None
    cpu_usage_nsec: Optional[int] = None
    tasks_current: Optional[int] = None
    state_change_timestamp: Optional[UTCDateTime] = None
    is_system_service: bool = False

    @property
    def status(self) -> str:
        if self.active_state == "failed":
            return "failed"
        if self.active_state == "active":
            return "running"
        if self.active_state == "inactive":
            return "stopped"
        return self.active_state or "unknown"

    @property
    def enabled(self) -> bool:
        return self.unit_file_state in {"enabled", "enabled-runtime", "static", "generated", "transient"}


class ServiceDetail(ServiceSummary):
    """Detailed service information for the service detail page."""

    names: list[str] = []
    user: Optional[str] = None
    group: Optional[str] = None
    restart: str = ""
    restart_usec: int = 0
    fragment_path: str = ""
    source_path: str = ""
    drop_in_paths: list[str] = []
    requires: list[str] = []
    requisite: list[str] = []
    wants: list[str] = []
    binds_to: list[str] = []
    part_of: list[str] = []
    conflicts: list[str] = []
    before: list[str] = []
    after: list[str] = []
    on_failure: list[str] = []
    refuses_manual_start: bool = False
    refuses_manual_stop: bool = False
    can_start: bool = True
    can_stop: bool = True
    can_reload: bool = False
    can_restart: bool = True


class ServiceListResponse(BaseModel):
    """Paginated/filtered service list response."""

    services: list[ServiceSummary]
    total: int
    show_system: bool = False
    state_filter: Optional[str] = None
    search: Optional[str] = None


class ServiceActionResponse(BaseModel):
    """Result of a service control action."""

    name: str
    action: str
    success: bool
    status: str
    message: str


class ServiceActionLogResponse(BaseModel):
    """Audit log entry for a service action."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    service_name: str
    action: str
    status: str
    detail: Optional[str]
    created_at: UTCDateTime
