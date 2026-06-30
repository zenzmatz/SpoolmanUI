"""Authentication helpers for the API and web client."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import HTTPException, Request, Response, WebSocket, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import HTTPConnection

from spoolman import env
from spoolman.database import auth as db_auth
from spoolman.database import models as db_models
from spoolman.database.database import db_session_context

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    """Get the current naive UTC timestamp."""
    return datetime.utcnow().replace(microsecond=0)


@dataclass
class AuthenticationContext:
    """Resolved authentication state for a request."""

    user: db_models.AuthUser
    session_hash: str | None = None
    api_token_id: int | None = None


def hash_password(password: str) -> str:
    """Hash a password using scrypt."""
    salt = secrets.token_bytes(16)
    n = 2**14
    r = 8
    p = 1
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p)
    return "$".join(
        [
            "scrypt",
            str(n),
            str(r),
            str(p),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(digest).decode("ascii"),
        ],
    )


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a stored scrypt hash."""
    try:
        algorithm, n_raw, r_raw, p_raw, salt_raw, digest_raw = password_hash.split("$", 5)
    except ValueError:
        return False

    if algorithm != "scrypt":
        return False

    try:
        n = int(n_raw)
        r = int(r_raw)
        p = int(p_raw)
        salt = base64.urlsafe_b64decode(salt_raw.encode("ascii"))
        digest = base64.urlsafe_b64decode(digest_raw.encode("ascii"))
    except (TypeError, ValueError):
        return False

    candidate = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p)
    return hmac.compare_digest(candidate, digest)


def hash_secret(secret: str) -> str:
    """Hash a bearer or session secret for storage."""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def create_session_secret() -> str:
    """Create a new raw session secret."""
    return f"spss_{secrets.token_urlsafe(32)}"


def create_api_token_secret() -> str:
    """Create a new raw API token secret."""
    return f"spat_{secrets.token_urlsafe(32)}"


def create_device_code_secret() -> str:
    """Create a short hardware pairing code."""
    return f"{secrets.randbelow(1000000):06d}"


def api_token_preview(raw_token: str) -> str:
    """Create a short preview string for a token."""
    return f"{raw_token[:12]}...{raw_token[-4:]}"


def session_cookie_path() -> str:
    """Resolve the cookie path from the configured base path."""
    base_path = env.get_base_path()
    return base_path if base_path else "/"


def set_session_cookie(response: Response, raw_session_secret: str) -> None:
    """Attach the auth session cookie to a response."""
    max_age = env.get_auth_session_ttl_hours() * 60 * 60
    response.set_cookie(
        key=env.get_auth_session_cookie_name(),
        value=raw_session_secret,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=env.is_auth_cookie_secure(),
        path=session_cookie_path(),
    )


def clear_session_cookie(response: Response) -> None:
    """Remove the auth session cookie from a response."""
    response.delete_cookie(
        key=env.get_auth_session_cookie_name(),
        path=session_cookie_path(),
        httponly=True,
        samesite="lax",
        secure=env.is_auth_cookie_secure(),
    )


async def _authenticate_connection(connection: HTTPConnection, db: AsyncSession) -> AuthenticationContext | None:
    auth_header = connection.headers.get("authorization")
    now = utcnow()

    if auth_header and auth_header.lower().startswith("bearer "):
        raw_token = auth_header[7:].strip()
        token_item = await db_auth.get_api_token_by_hash(db, hash_secret(raw_token))
        if token_item is not None:
            if token_item.revoked_at is not None:
                return None
            if token_item.expires_at is not None and token_item.expires_at <= now:
                token_item.revoked_at = now
                return None
            token_item.last_used = now
            return AuthenticationContext(user=token_item.user, api_token_id=token_item.id)

    raw_session_secret = connection.cookies.get(env.get_auth_session_cookie_name())
    if not raw_session_secret:
        return None

    session_item = await db_auth.get_session_by_hash(db, hash_secret(raw_session_secret))
    if session_item is None:
        return None
    if session_item.expires_at <= now:
        await db.delete(session_item)
        return None

    session_item.last_used = now
    return AuthenticationContext(user=session_item.user, session_hash=session_item.session_hash)


async def authenticate_request(request: Request, db: AsyncSession) -> AuthenticationContext | None:
    """Resolve the auth context for an HTTP request."""
    return await _authenticate_connection(request, db)


def require_authenticated_context(request: Request) -> AuthenticationContext:
    """Get the auth context placed on the request by the auth middleware."""
    if not env.is_auth_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Authentication is disabled.")

    context = getattr(request.state, "auth_context", None)
    if context is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return context


def require_authenticated_user(request: Request) -> db_models.AuthUser:
    """Get the authenticated user from request state."""
    return require_authenticated_context(request).user


async def enforce_websocket_auth_if_enabled(websocket: WebSocket) -> bool:
    """Validate websocket auth if the auth system is enabled."""
    if not env.is_auth_enabled():
        return True

    async with db_session_context() as db:
        context = await _authenticate_connection(websocket, db)
        if context is None:
            await websocket.close(code=4401, reason="Authentication required.")
            return False

    return True


async def bootstrap_auth_admin() -> None:
    """Ensure the bootstrap admin exists when auth is enabled."""
    if not env.is_auth_enabled():
        return

    username = env.get_auth_admin_username()
    bootstrap_password = env.get_auth_admin_password()

    async with db_session_context() as db:
        existing_user = await db_auth.get_user_by_username(db, username)
        if existing_user is not None:
            return

        if bootstrap_password is None or bootstrap_password == "":
            raise RuntimeError(
                "Authentication is enabled, but no bootstrap admin exists and no SPOOLMAN_AUTH_ADMIN_PASSWORD "
                "or SPOOLMAN_AUTH_ADMIN_PASSWORD_FILE was provided.",
            )

        await db_auth.create_user(
            db,
            username=username,
            password_hash=hash_password(bootstrap_password),
            is_admin=True,
            created=utcnow(),
        )

    if not env.is_auth_cookie_secure() and not env.is_debug_mode():
        logger.warning(
            "Authentication is enabled but SPOOLMAN_AUTH_COOKIE_SECURE is false. "
            "Enable it when Spoolman is served over HTTPS.",
        )
    logger.warning(
        "Created bootstrap admin user '%s'. Remove SPOOLMAN_AUTH_ADMIN_PASSWORD from long-term configuration once "
        "you can log in successfully.",
        username,
    )