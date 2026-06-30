"""Authentication-related database helpers."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from spoolman.database import models


async def get_user_by_username(db: AsyncSession, username: str) -> models.AuthUser | None:
    """Get a user by username."""
    result = await db.execute(select(models.AuthUser).where(models.AuthUser.username == username))
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    *,
    username: str,
    password_hash: str,
    is_admin: bool,
    created: datetime,
) -> models.AuthUser:
    """Create a new auth user."""
    item = models.AuthUser(
        username=username,
        password_hash=password_hash,
        is_admin=is_admin,
        created=created,
        last_login=None,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


async def get_session_by_hash(db: AsyncSession, session_hash: str) -> models.AuthSession | None:
    """Get a session by its hashed secret."""
    result = await db.execute(
        select(models.AuthSession)
        .options(joinedload(models.AuthSession.user))
        .where(models.AuthSession.session_hash == session_hash),
    )
    return result.scalar_one_or_none()


async def create_session(
    db: AsyncSession,
    *,
    user_id: int,
    session_hash: str,
    created: datetime,
    expires_at: datetime,
) -> models.AuthSession:
    """Create a new session."""
    item = models.AuthSession(
        user_id=user_id,
        session_hash=session_hash,
        created=created,
        last_used=created,
        expires_at=expires_at,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


async def delete_session_by_hash(db: AsyncSession, session_hash: str) -> None:
    """Delete a session by its hashed secret."""
    item = await get_session_by_hash(db, session_hash)
    if item is not None:
        await db.delete(item)


async def get_api_token_by_hash(db: AsyncSession, token_hash: str) -> models.AuthApiToken | None:
    """Get an API token by its hashed secret."""
    result = await db.execute(
        select(models.AuthApiToken)
        .options(joinedload(models.AuthApiToken.user))
        .where(models.AuthApiToken.token_hash == token_hash),
    )
    return result.scalar_one_or_none()


async def list_api_tokens_for_user(db: AsyncSession, user_id: int) -> list[models.AuthApiToken]:
    """List API tokens for a user."""
    result = await db.execute(
        select(models.AuthApiToken)
        .where(models.AuthApiToken.user_id == user_id)
        .order_by(models.AuthApiToken.created.desc()),
    )
    return list(result.scalars().all())


async def create_api_token(
    db: AsyncSession,
    *,
    user_id: int,
    name: str,
    token_preview: str,
    token_hash: str,
    created: datetime,
    expires_at: datetime | None,
) -> models.AuthApiToken:
    """Create an API token."""
    item = models.AuthApiToken(
        user_id=user_id,
        name=name,
        token_preview=token_preview,
        token_hash=token_hash,
        created=created,
        last_used=None,
        expires_at=expires_at,
        revoked_at=None,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


async def get_api_token_for_user(db: AsyncSession, token_id: int, user_id: int) -> models.AuthApiToken | None:
    """Get an API token owned by the specified user."""
    result = await db.execute(
        select(models.AuthApiToken).where(
            models.AuthApiToken.id == token_id,
            models.AuthApiToken.user_id == user_id,
        ),
    )
    return result.scalar_one_or_none()


async def create_device_code(
    db: AsyncSession,
    *,
    user_id: int,
    name: str,
    code_preview: str,
    code_hash: str,
    created: datetime,
    expires_at: datetime,
) -> models.AuthDeviceCode:
    """Create a short-lived hardware pairing code."""
    item = models.AuthDeviceCode(
        user_id=user_id,
        name=name,
        code_preview=code_preview,
        code_hash=code_hash,
        created=created,
        expires_at=expires_at,
        used_at=None,
        token_id=None,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


async def get_device_code_by_hash(db: AsyncSession, code_hash: str) -> models.AuthDeviceCode | None:
    """Get a hardware pairing code by its hashed secret."""
    result = await db.execute(
        select(models.AuthDeviceCode)
        .options(joinedload(models.AuthDeviceCode.user))
        .where(models.AuthDeviceCode.code_hash == code_hash),
    )
    return result.scalar_one_or_none()