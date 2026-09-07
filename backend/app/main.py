"""Nexus API FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.config import settings
from app.database import Base, engine
from app.database import SessionLocal
from app.routes import auth, features, files, health, logs, processes, services, settings as settings_router, storage, system, terminal, updates, users
from app.services.settings import seed_defaults


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables and seed default settings on startup."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Migration: add sudo_username to admin_sessions if it does not exist.
        from sqlalchemy import text
        from sqlalchemy.exc import OperationalError

        try:
            db.execute(text("ALTER TABLE admin_sessions ADD COLUMN sudo_username VARCHAR"))
            db.commit()
        except OperationalError:
            db.rollback()
        try:
            db.execute(text("ALTER TABLE users ADD COLUMN auth_source VARCHAR DEFAULT 'local'"))
            db.commit()
        except OperationalError:
            db.rollback()
        seed_defaults(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="Nexus API",
    description="Backend API for the Nexus Panel server management platform.",
    version=__version__,
    docs_url="/api/docs" if not settings.is_production else None,
    redoc_url="/api/redoc" if not settings.is_production else None,
    openapi_url="/api/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
)

# CORS: restrict to configured origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def cache_control_header(request: Request, call_next):
    """Force revalidation of non-API responses so UI changes deploy instantly."""
    response = await call_next(request)
    if not request.url.path.startswith("/api"):
        response.headers.setdefault("Cache-Control", "no-cache")
    return response


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a generic error response without leaking internals in production."""
    message = "Internal server error"
    if not settings.is_production:
        message = f"{type(exc).__name__}: {str(exc)}"
    return JSONResponse(
        status_code=500,
        content={"detail": message},
    )


# API routes.
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
app.include_router(services.router, prefix="/api/v1")
app.include_router(processes.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(logs.router, prefix="/api/v1")
app.include_router(updates.router, prefix="/api/v1")
app.include_router(features.router, prefix="/api/v1")
app.include_router(storage.router, prefix="/api/v1")
app.include_router(files.router, prefix="/api/v1")
app.include_router(settings_router.router, prefix="/api/v1")
if settings.terminal_enabled:
    app.include_router(terminal.router, prefix="/api/v1")


# Static frontend files (HTML/CSS/JS).
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


@app.get("/", include_in_schema=False)
def root_page() -> RedirectResponse:
    """Redirect root to the overview page."""
    return RedirectResponse(url="/overview")


@app.get("/login", include_in_schema=False)
def login_page() -> FileResponse:
    """Serve the login page."""
    return FileResponse(FRONTEND_DIR / "login.html")


@app.get("/overview", include_in_schema=False)
def overview_page() -> FileResponse:
    """Serve the overview page."""
    return FileResponse(FRONTEND_DIR / "overview.html")


@app.get("/health", include_in_schema=False)
def health_page() -> FileResponse:
    """Serve the health page."""
    return FileResponse(FRONTEND_DIR / "health.html")


@app.get("/services", include_in_schema=False)
def services_page() -> FileResponse:
    """Serve the services page."""
    return FileResponse(FRONTEND_DIR / "services.html")


@app.get("/service-detail", include_in_schema=False)
def service_detail_page() -> FileResponse:
    """Serve the service detail page."""
    return FileResponse(FRONTEND_DIR / "service-detail.html")


@app.get("/updates", include_in_schema=False)
def updates_page() -> FileResponse:
    """Serve the updates page."""
    return FileResponse(FRONTEND_DIR / "updates.html")


@app.get("/terminal", include_in_schema=False)
def terminal_page() -> FileResponse:
    """Serve the terminal page."""
    return FileResponse(FRONTEND_DIR / "terminal.html")


@app.get("/storage", include_in_schema=False)
def storage_page() -> FileResponse:
    """Serve the storage / drives page."""
    return FileResponse(FRONTEND_DIR / "storage.html")


@app.get("/processes", include_in_schema=False)
def processes_page() -> FileResponse:
    """Serve the processes page."""
    return FileResponse(FRONTEND_DIR / "processes.html")


@app.get("/users", include_in_schema=False)
def users_page() -> FileResponse:
    """Serve the users page."""
    return FileResponse(FRONTEND_DIR / "users.html")


@app.get("/drive-detail", include_in_schema=False)
def drive_detail_page() -> FileResponse:
    """Serve the drive detail page."""
    return FileResponse(FRONTEND_DIR / "drive-detail.html")


@app.get("/files", include_in_schema=False)
def files_page() -> FileResponse:
    """Serve the file manager page."""
    return FileResponse(FRONTEND_DIR / "files.html")


@app.get("/settings", include_in_schema=False)
def settings_page() -> FileResponse:
    """Serve the settings page."""
    return FileResponse(FRONTEND_DIR / "settings.html")


@app.get("/dashboard", include_in_schema=False)
def dashboard_page() -> RedirectResponse:
    """Redirect old dashboard route to overview."""
    return RedirectResponse(url="/overview")


class RevalidatingStaticFiles(StaticFiles):
    """Static files that must revalidate (ETag/If-Modified-Since) before use."""

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


if FRONTEND_DIR.exists():
    app.mount("/", RevalidatingStaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
