"""Add source_url column to messenger_room_mappings

Revision ID: 004_room_source_url
Revises: 003_device_token
Create Date: 2026-09-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004_room_source_url"
down_revision: Union[str, None] = "003_device_token"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("messenger_room_mappings")]

    if "source_url" not in columns:
        op.add_column(
            "messenger_room_mappings",
            sa.Column("source_url", sa.String(1000), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("messenger_room_mappings", "source_url")
