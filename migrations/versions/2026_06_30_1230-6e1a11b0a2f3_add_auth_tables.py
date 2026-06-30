"""Add authentication tables.

Revision ID: 6e1a11b0a2f3
Revises: 415a8f855e14
Create Date: 2026-06-30 12:30:00.000000
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6e1a11b0a2f3"
down_revision = "415a8f855e14"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Perform the upgrade."""
    op.create_table(
        "auth_user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("last_login", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auth_user_id"), "auth_user", ["id"], unique=False)
    op.create_index(op.f("ix_auth_user_username"), "auth_user", ["username"], unique=True)

    op.create_table(
        "auth_session",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("session_hash", sa.String(length=64), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("last_used", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["auth_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auth_session_id"), "auth_session", ["id"], unique=False)
    op.create_index(op.f("ix_auth_session_session_hash"), "auth_session", ["session_hash"], unique=True)
    op.create_index(op.f("ix_auth_session_user_id"), "auth_session", ["user_id"], unique=False)

    op.create_table(
        "auth_api_token",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("token_preview", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("last_used", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["auth_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auth_api_token_id"), "auth_api_token", ["id"], unique=False)
    op.create_index(op.f("ix_auth_api_token_token_hash"), "auth_api_token", ["token_hash"], unique=True)
    op.create_index(op.f("ix_auth_api_token_user_id"), "auth_api_token", ["user_id"], unique=False)

    op.create_table(
        "auth_device_code",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("code_preview", sa.String(length=16), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("token_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["token_id"], ["auth_api_token.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["auth_user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auth_device_code_code_hash"), "auth_device_code", ["code_hash"], unique=True)
    op.create_index(op.f("ix_auth_device_code_id"), "auth_device_code", ["id"], unique=False)
    op.create_index(op.f("ix_auth_device_code_token_id"), "auth_device_code", ["token_id"], unique=False)
    op.create_index(op.f("ix_auth_device_code_user_id"), "auth_device_code", ["user_id"], unique=False)


def downgrade() -> None:
    """Perform the downgrade."""
    op.drop_index(op.f("ix_auth_device_code_user_id"), table_name="auth_device_code")
    op.drop_index(op.f("ix_auth_device_code_token_id"), table_name="auth_device_code")
    op.drop_index(op.f("ix_auth_device_code_id"), table_name="auth_device_code")
    op.drop_index(op.f("ix_auth_device_code_code_hash"), table_name="auth_device_code")
    op.drop_table("auth_device_code")

    op.drop_index(op.f("ix_auth_api_token_user_id"), table_name="auth_api_token")
    op.drop_index(op.f("ix_auth_api_token_token_hash"), table_name="auth_api_token")
    op.drop_index(op.f("ix_auth_api_token_id"), table_name="auth_api_token")
    op.drop_table("auth_api_token")

    op.drop_index(op.f("ix_auth_session_user_id"), table_name="auth_session")
    op.drop_index(op.f("ix_auth_session_session_hash"), table_name="auth_session")
    op.drop_index(op.f("ix_auth_session_id"), table_name="auth_session")
    op.drop_table("auth_session")

    op.drop_index(op.f("ix_auth_user_username"), table_name="auth_user")
    op.drop_index(op.f("ix_auth_user_id"), table_name="auth_user")
    op.drop_table("auth_user")