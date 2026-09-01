"""Add messenger_device_tokens table for FCM push notifications

Revision ID: 003_device_token
Revises: 002_ext_client
Create Date: 2026-09-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_device_token"
down_revision: Union[str, None] = "002_ext_client"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "messenger_device_tokens" in inspector.get_table_names():
        return

    op.create_table(
        "messenger_device_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("hub_user_id", sa.String(255), nullable=False, index=True),
        sa.Column("fcm_token", sa.String(500), nullable=False, unique=True),
        sa.Column("platform", sa.String(20), nullable=False, server_default="android"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("messenger_device_tokens")
