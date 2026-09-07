"""System updates request/response schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class UpdateInfo(BaseModel):
    """Information about available system package updates."""

    supported: bool
    package_manager: str | None
    update_count: int
    packages: list[str]
    error: str | None
    last_checked: str | None
    reboot_required: bool = False


class ApplyUpdatesRequest(BaseModel):
    """Request to apply available system updates."""

    reboot: bool = Field(False, description="Reboot the machine after updates finish successfully")


class UpdateOperationResponse(BaseModel):
    """Response from an update operation."""

    success: bool
    message: str
    reboot_scheduled: bool = False
