"""Add archived_at column to messenger_room_mappings

Revision ID: 007_room_archived_at
Revises: 006_room_read_tracking
Create Date: 2026-09-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007_room_archived_at"
down_revision: Union[str, None] = "006_room_read_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("messenger_room_mappings")]

    if "archived_at" not in columns:
        op.add_column(
            "messenger_room_mappings",
            sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("messenger_room_mappings", "archived_at")
