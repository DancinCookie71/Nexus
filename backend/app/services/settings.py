"""Settings storage and defaults."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings as app_settings
from app.models import Setting


# Default settings organized by category. Values are strings to keep storage
# uniform; consumers are responsible for parsing booleans/ints when needed.
DEFAULT_SETTINGS: dict[str, dict[str, str]] = {
    "nexus": {
        "app_name": "Nexus Panel",
        "session_lifetime_minutes": str(app_settings.session_lifetime_minutes),
        "admin_session_lifetime_minutes": str(app_settings.admin_session_lifetime_minutes),
        "terminal_enabled": "true",
        "terminal_max_sessions_per_user": str(app_settings.terminal_max_sessions_per_user),
        "terminal_shell": app_settings.terminal_shell,
        "files_root": app_settings.files_root,
    },
    "server": {
        "service_allowlist": app_settings.service_allowlist,
        "host": app_settings.host,
        "port": str(app_settings.port),
    },
    "security": {
        "require_admin_for_terminal": "false",
        "require_admin_for_files_writes": "false",
        "max_login_attempts": "5",
        "login_lockout_minutes": "5",
    },
    "ui": {
        "theme": "dark",
        "page_title": "Nexus Panel",
        "refresh_interval_seconds": "2",
    },
    "logging": {
        "log_level": "info",
        "audit_log_retention_days": "30",
    },
    "notifications": {
        "email_alerts_enabled": "false",
        "alert_email": "",
    },
}


def seed_defaults(db: Session) -> None:
    """Insert default settings that do not already exist."""
    for category, items in DEFAULT_SETTINGS.items():
        for key, value in items.items():
            existing = db.query(Setting).filter(Setting.key == key).first()
            if existing is None:
                db.add(Setting(key=key, value=value, category=category))
    db.commit()


def get_setting(db: Session, key: str, default: str | None = None) -> str | None:
    """Return the value of a setting, or a default if it does not exist."""
    setting = db.query(Setting).filter(Setting.key == key).first()
    return setting.value if setting else default


def get_setting_bool(db: Session, key: str, default: bool = False) -> bool:
    """Return a setting parsed as a boolean."""
    raw = get_setting(db, key)
    if raw is None:
        return default
    return raw.strip().lower() in {"true", "1", "yes", "on"}


def get_setting_int(db: Session, key: str, default: int = 0) -> int:
    """Return a setting parsed as an integer."""
    raw = get_setting(db, key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def get_settings_by_category(db: Session) -> dict[str, dict[str, str]]:
    """Return all settings grouped by category."""
    categories: dict[str, dict[str, str]] = {}
    for setting in db.query(Setting).order_by(Setting.category, Setting.key).all():
        categories.setdefault(setting.category, {})[setting.key] = setting.value
    # Ensure every default category appears even if empty.
    for category in DEFAULT_SETTINGS:
        categories.setdefault(category, {})
    return categories


def get_all_settings(db: Session) -> list[Setting]:
    """Return all settings ordered by category and key."""
    return db.query(Setting).order_by(Setting.category, Setting.key).all()


def set_setting(db: Session, key: str, value: str, category: str | None = None) -> Setting:
    """Create or update a setting."""
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting is None:
        resolved_category = category or "general"
        setting = Setting(key=key, value=value, category=resolved_category)
        db.add(setting)
    else:
        setting.value = value
        if category is not None:
            setting.category = category
    db.commit()
    db.refresh(setting)
    return setting


def delete_setting(db: Session, key: str) -> bool:
    """Delete a setting. Returns True if it existed."""
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting is None:
        return False
    db.delete(setting)
    db.commit()
    return True
