"""Add role_api_scopes association table

Revision ID: 595d9ef40762
Revises: 40da687f0d4d
Create Date: 2025-12-17 13:12:20.396361

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "595d9ef40762"
down_revision: Union[str, Sequence[str], None] = "ea167a6ca3c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create role_api_scopes association table."""
    op.create_table(
        "role_api_scopes",
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("api_scope_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["api_scope_id"], ["api_scopes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "api_scope_id"),
    )


def downgrade() -> None:
    """Drop role_api_scopes association table."""
    op.drop_table("role_api_scopes")
