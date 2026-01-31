"""Add role column to messenger_user_mappings

Revision ID: 001_add_role
Revises: None
Create Date: 2026-01-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_add_role"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add column only if it doesn't already exist (idempotent)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("messenger_user_mappings")]
    if "role" not in columns:
        op.add_column(
            "messenger_user_mappings",
            sa.Column("role", sa.String(50), nullable=False, server_default="user"),
        )


def downgrade() -> None:
    op.drop_column("messenger_user_mappings", "role")
