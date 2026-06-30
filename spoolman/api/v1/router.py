"""Router setup for the v1 version of the API."""

# ruff: noqa: D103

import asyncio
import logging

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from starlette.responses import Response

from spoolman import env
from spoolman.auth import authenticate_request, enforce_websocket_auth_if_enabled
from spoolman.database.database import backup_global_db, db_session_context
from spoolman.exceptions import ItemNotFoundError
from spoolman.ws import websocket_manager

from . import auth, export, externaldb, field, filament, insights, models, other, setting, spool, vendor

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Spoolman REST API v1",
    version="1.0.0",
    docs_url=None if env.is_auth_enabled() else "/docs",
    redoc_url=None if env.is_auth_enabled() else "/redoc",
    openapi_url=None if env.is_auth_enabled() else "/openapi.json",
    description="""
    REST API for Spoolman.

    The API is served on the path `/api/v1/`.

    Some endpoints also serve a websocket on the same path. The websocket is used to listen for changes to the data
    that the endpoint serves. The websocket messages are JSON objects. Additionally, there is a root-level websocket
    endpoint that listens for changes to any data in the database.
    """,
)

PUBLIC_PATHS = {
    "/auth/login",
    "/auth/status",
    "/auth/devices/register",
    "/health",
}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    request_path = request.scope.get("path", "")
    root_path = request.scope.get("root_path", "")
    if root_path and request_path.startswith(root_path):
        request_path = request_path[len(root_path) :] or "/"
    if not env.is_auth_enabled() or request_path in PUBLIC_PATHS:
        return await call_next(request)

    async with db_session_context() as db:
        auth_context = await authenticate_request(request, db)
        if auth_context is None:
            return JSONResponse(status_code=401, content={"message": "Authentication required."})
        request.state.auth_context = auth_context

    return await call_next(request)


@app.exception_handler(ItemNotFoundError)
async def itemnotfounderror_exception_handler(_request: Request, exc: ItemNotFoundError) -> Response:
    logger.debug(exc)
    return JSONResponse(
        status_code=404,
        content={"message": exc.args[0]},
    )


# Add a general info endpoint
@app.get("/info")
async def info() -> models.Info:
    """Return general info about the API."""
    return models.Info(
        version=env.get_version(),
        debug_mode=env.is_debug_mode(),
        automatic_backups=env.is_automatic_backup_enabled(),
        data_dir=str(env.get_data_dir().resolve()),
        logs_dir=str(env.get_logs_dir().resolve()),
        backups_dir=str(env.get_backups_dir().resolve()),
        db_type=str(env.get_database_type() or "sqlite"),
        git_commit=env.get_commit_hash(),
        build_date=env.get_build_date(),
    )


# Add health check endpoint
@app.get("/health")
async def health() -> models.HealthCheck:
    """Return a health check."""
    return models.HealthCheck(status="healthy")


# Add endpoint for triggering a db backup
@app.post(
    "/backup",
    description="Trigger a database backup. Only applicable for SQLite databases.",
    response_model=models.BackupResponse,
    responses={500: {"model": models.Message}},
)
async def backup():  # noqa: ANN201
    """Trigger a database backup."""
    path = await backup_global_db()
    if path is None:
        return JSONResponse(
            status_code=500,
            content={"message": "Backup failed. See server logs for more information."},
        )
    return models.BackupResponse(path=str(path))


@app.websocket(
    "/",
    name="Listen to any changes",
)
async def notify(
    websocket: WebSocket,
) -> None:
    if not await enforce_websocket_auth_if_enabled(websocket):
        return
    await websocket.accept()
    websocket_manager.connect((), websocket)
    try:
        while True:
            await asyncio.sleep(0.5)
            if await websocket.receive_text():
                await websocket.send_json({"status": "healthy"})
    except WebSocketDisconnect:
        websocket_manager.disconnect((), websocket)


# Add routers
app.include_router(auth.router)
app.include_router(filament.router)
app.include_router(spool.router)
app.include_router(vendor.router)
app.include_router(setting.router)
app.include_router(field.router)
app.include_router(insights.router)
app.include_router(other.router)
app.include_router(externaldb.router)
app.include_router(export.router)
