"""Add matrix_password and external_client_enabled columns

Revision ID: 002_ext_client
Revises: 001_add_role
Create Date: 2026-01-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_ext_client"
down_revision: Union[str, None] = "001_add_role"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("messenger_user_mappings")]

    if "matrix_password" not in columns:
        op.add_column(
            "messenger_user_mappings",
            sa.Column("matrix_password", sa.String(255), nullable=True),
        )
    if "external_client_enabled" not in columns:
        op.add_column(
            "messenger_user_mappings",
            sa.Column("external_client_enabled", sa.Boolean(), nullable=False, server_default="false"),
        )


def downgrade() -> None:
    op.drop_column("messenger_user_mappings", "external_client_enabled")
    op.drop_column("messenger_user_mappings", "matrix_password")
