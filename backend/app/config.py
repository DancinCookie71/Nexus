"""Application configuration loaded from environment variables."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Nexus API settings."""

    model_config = SettingsConfigDict(
        env_prefix="NEXUS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    secret_key: str
    host: str = "0.0.0.0"
    port: int = 8000
    env: str = "development"
    database_url: str = "sqlite:///./data/nexus.db"
    session_lifetime_minutes: int = 1440
    admin_session_lifetime_minutes: int = 0
    cors_origins: str = "http://localhost:8000"
    service_allowlist: str = "nginx,postgresql"
    terminal_shell: str = "/bin/bash"
    terminal_max_sessions_per_user: int = 2
    files_root: str = "/home/nexus"

    @property
    def terminal_enabled(self) -> bool:
        """Return whether the interactive terminal is enabled.

        Controlled by NEXUS_TERMINAL_ENABLED (the legacy TERMINAL variable
        is still accepted).
        """
        raw = os.environ.get("NEXUS_TERMINAL_ENABLED", os.environ.get("TERMINAL", "true"))
        return raw.lower() == "true"

    @property
    def cors_origins_list(self) -> List[str]:
        """Return CORS origins as a list from comma-separated or JSON env value."""
        value = self.cors_origins.strip()
        if value.startswith("["):
            return json.loads(value)
        return [item.strip() for item in value.split(",") if item.strip()]

    @property
    def service_allowlist_set(self) -> set[str]:
        """Return the configured service allowlist as a set."""
        return {item.strip() for item in self.service_allowlist.split(",") if item.strip()}

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"

    @property
    def database_path(self) -> Path:
        """Return the filesystem path for a SQLite database URL."""
        if self.database_url.startswith("sqlite:///./"):
            return Path(self.database_url.replace("sqlite:///./", ""))
        if self.database_url.startswith("sqlite:////"):
            return Path(self.database_url.replace("sqlite:////", ""))
        raise ValueError("Only SQLite relative or absolute paths are supported")


settings = Settings()
