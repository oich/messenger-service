"""Add last_message_at to messenger_room_mappings + messenger_room_reads table

Revision ID: 006_room_read_tracking
Revises: 005_add_teams
Create Date: 2026-09-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006_room_read_tracking"
down_revision: Union[str, None] = "005_add_teams"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    columns = [c["name"] for c in inspector.get_columns("messenger_room_mappings")]
    if "last_message_at" not in columns:
        op.add_column(
            "messenger_room_mappings",
            sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        )

    if "messenger_room_reads" not in inspector.get_table_names():
        op.create_table(
            "messenger_room_reads",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("hub_user_id", sa.String(255), nullable=False, index=True),
            sa.Column("matrix_room_id", sa.String(255), nullable=False, index=True),
            sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("hub_user_id", "matrix_room_id", name="_room_read_uc"),
        )


def downgrade() -> None:
    op.drop_table("messenger_room_reads")
    op.drop_column("messenger_room_mappings", "last_message_at")
