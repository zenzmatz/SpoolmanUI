"""Authentication endpoints."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from spoolman import env
from spoolman.api.v1.models import Message, SpoolmanDateTime
from spoolman.auth import (
    api_token_preview,
    clear_session_cookie,
    create_api_token_secret,
    create_device_code_secret,
    create_session_secret,
    hash_secret,
    require_authenticated_context,
    require_authenticated_user,
    set_session_cookie,
    utcnow,
    verify_password,
)
from spoolman.database import auth as db_auth
from spoolman.database import models as db_models
from spoolman.database.database import get_db_session

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


class AuthStatusResponse(BaseModel):
    enabled: bool = Field()


class AuthUserResponse(BaseModel):
    id: int = Field()
    username: str = Field()
    is_admin: bool = Field()
    created: SpoolmanDateTime = Field()
    last_login: SpoolmanDateTime | None = Field(None)

    @staticmethod
    def from_db(item: db_models.AuthUser) -> "AuthUserResponse":
        return AuthUserResponse(
            id=item.id,
            username=item.username,
            is_admin=item.is_admin,
            created=item.created,
            last_login=item.last_login,
        )


class LoginParameters(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=512)


class AuthTokenParameters(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    expires_in_days: int | None = Field(default=365, ge=1, le=3650)


class AuthTokenResponse(BaseModel):
    id: int = Field()
    name: str = Field()
    token_preview: str = Field()
    created: SpoolmanDateTime = Field()
    last_used: SpoolmanDateTime | None = Field(None)
    expires_at: SpoolmanDateTime | None = Field(None)
    revoked_at: SpoolmanDateTime | None = Field(None)

    @staticmethod
    def from_db(item: db_models.AuthApiToken) -> "AuthTokenResponse":
        return AuthTokenResponse(
            id=item.id,
            name=item.name,
            token_preview=item.token_preview,
            created=item.created,
            last_used=item.last_used,
            expires_at=item.expires_at,
            revoked_at=item.revoked_at,
        )


class AuthTokenCreateResponse(BaseModel):
    token: str = Field()
    token_info: AuthTokenResponse = Field()


class AuthDeviceCodeParameters(BaseModel):
    name: str = Field(default="SpoolmanScale", min_length=1, max_length=128)
    expires_in_minutes: int = Field(default=15, ge=1, le=1440)


class AuthDeviceCodeCreateResponse(BaseModel):
    code: str = Field()
    name: str = Field()
    expires_at: SpoolmanDateTime = Field()


class AuthDeviceRegisterParameters(BaseModel):
    device_name: str = Field(default="Hardware device", min_length=1, max_length=128)


@router.get("/status", response_model=AuthStatusResponse)
async def status_endpoint() -> AuthStatusResponse:
    """Return whether authentication is enabled."""
    return AuthStatusResponse(enabled=env.is_auth_enabled())


@router.post(
    "/login",
    response_model=AuthUserResponse,
    responses={401: {"model": Message}, 404: {"model": Message}},
)
async def login(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    response: Response,
    body: LoginParameters,
) -> AuthUserResponse | JSONResponse:
    """Create an authenticated browser session."""
    if not env.is_auth_enabled():
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=Message(message="Authentication is disabled.").model_dump(),
        )

    user = await db_auth.get_user_by_username(db, body.username.strip())
    if user is None or not verify_password(body.password, user.password_hash):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=Message(message="Invalid username or password.").model_dump(),
        )

    now = utcnow()
    user.last_login = now
    raw_session_secret = create_session_secret()
    await db_auth.create_session(
        db,
        user_id=user.id,
        session_hash=hash_secret(raw_session_secret),
        created=now,
        expires_at=now + timedelta(hours=env.get_auth_session_ttl_hours()),
    )
    set_session_cookie(response, raw_session_secret)
    return AuthUserResponse.from_db(user)


@router.post("/logout", response_model=Message)
async def logout(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    _current_user: Annotated[db_models.AuthUser, Depends(require_authenticated_user)],
) -> Message:
    """Log out the current session or revoke the current API token."""
    context = require_authenticated_context(request)
    if context.session_hash is not None:
        await db_auth.delete_session_by_hash(db, context.session_hash)
    elif context.api_token_id is not None:
        token = await db_auth.get_api_token_for_user(db, context.api_token_id, context.user.id)
        if token is not None:
            token.revoked_at = utcnow()
    clear_session_cookie(response)
    return Message(message="Logged out.")


@router.get("/me", response_model=AuthUserResponse)
async def me(current_user: Annotated[db_models.AuthUser, Depends(require_authenticated_user)]) -> AuthUserResponse:
    """Return the authenticated user."""
    return AuthUserResponse.from_db(current_user)


@router.get("/tokens", response_model=list[AuthTokenResponse])
async def list_tokens(
    current_user: Annotated[db_models.AuthUser, Depends(require_authenticated_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[AuthTokenResponse]:
    """List the current user's API tokens."""
    items = await db_auth.list_api_tokens_for_user(db, current_user.id)
    return [AuthTokenResponse.from_db(item) for item in items]


@router.post("/tokens", response_model=AuthTokenCreateResponse)
async def create_token(
    current_user: Annotated[db_models.AuthUser, Depends(require_authenticated_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    body: Annotated[AuthTokenParameters, Body()],
) -> AuthTokenCreateResponse | JSONResponse:
    """Create a new API token for the current user."""
    token_name = body.name.strip()
    if token_name == "":
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=Message(message="Token name must not be empty.").model_dump(),
        )

    raw_token = create_api_token_secret()
    now = utcnow()
    expires_at = now + timedelta(days=body.expires_in_days) if body.expires_in_days is not None else None
    db_item = await db_auth.create_api_token(
        db,
        user_id=current_user.id,
        name=token_name,
        token_preview=api_token_preview(raw_token),
        token_hash=hash_secret(raw_token),
        created=now,
        expires_at=expires_at,
    )
    return AuthTokenCreateResponse(token=raw_token, token_info=AuthTokenResponse.from_db(db_item))


@router.delete("/tokens/{token_id}", response_model=Message, responses={404: {"model": Message}})
async def revoke_token(
    token_id: int,
    current_user: Annotated[db_models.AuthUser, Depends(require_authenticated_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Message | JSONResponse:
    """Revoke one API token owned by the current user."""
    token = await db_auth.get_api_token_for_user(db, token_id, current_user.id)
    if token is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=Message(message="Token not found.").model_dump(),
        )

    token.revoked_at = utcnow()
    return Message(message="Token revoked.")


@router.post("/device-codes", response_model=AuthDeviceCodeCreateResponse)
async def create_device_code(
    current_user: Annotated[db_models.AuthUser, Depends(require_authenticated_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
    body: Annotated[AuthDeviceCodeParameters, Body()],
) -> AuthDeviceCodeCreateResponse | JSONResponse:
    """Create a short-lived hardware pairing code."""
    code_name = body.name.strip()
    if code_name == "":
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=Message(message="Device name must not be empty.").model_dump(),
        )

    raw_code = create_device_code_secret()
    now = utcnow()
    expires_at = now + timedelta(minutes=body.expires_in_minutes)
    await db_auth.create_device_code(
        db,
        user_id=current_user.id,
        name=code_name,
        code_preview=raw_code,
        code_hash=hash_secret(raw_code),
        created=now,
        expires_at=expires_at,
    )
    return AuthDeviceCodeCreateResponse(code=raw_code, name=code_name, expires_at=expires_at)


@router.post(
    "/devices/register",
    response_model=AuthTokenCreateResponse,
    responses={401: {"model": Message}, 404: {"model": Message}},
)
async def register_device(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    body: AuthDeviceRegisterParameters,
    request: Request,
) -> AuthTokenCreateResponse | JSONResponse:
    """Exchange a short hardware pairing code for a long-lived API token."""
    if not env.is_auth_enabled():
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=Message(message="Authentication is disabled.").model_dump(),
        )

    raw_code = request.headers.get("x-device-code", "").strip()
    if raw_code == "":
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=Message(message="Missing hardware pairing code.").model_dump(),
        )

    now = utcnow()
    device_code = await db_auth.get_device_code_by_hash(db, hash_secret(raw_code))
    if device_code is None or device_code.used_at is not None or device_code.expires_at <= now:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=Message(message="Invalid or expired hardware pairing code.").model_dump(),
        )

    raw_token = create_api_token_secret()
    device_name = body.device_name.strip()
    db_item = await db_auth.create_api_token(
        db,
        user_id=device_code.user_id,
        name=f"Hardware: {device_name}",
        token_preview=api_token_preview(raw_token),
        token_hash=hash_secret(raw_token),
        created=now,
        expires_at=None,
    )
    device_code.used_at = now
    device_code.token_id = db_item.id
    return AuthTokenCreateResponse(token=raw_token, token_info=AuthTokenResponse.from_db(db_item))