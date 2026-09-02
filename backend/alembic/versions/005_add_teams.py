"""Add messenger_teams table

Revision ID: 005_add_teams
Revises: 004_room_source_url
Create Date: 2026-09-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005_add_teams"
down_revision: Union[str, None] = "004_room_source_url"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "messenger_teams" not in inspector.get_table_names():
        op.create_table(
            "messenger_teams",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("name", sa.String(255), nullable=False, unique=True),
            sa.Column("member_hub_user_ids", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("messenger_teams")
