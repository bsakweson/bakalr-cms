"""Add api_scopes table

Revision ID: 40da687f0d4d
Revises: ea167a6ca3c7
Create Date: 2025-12-17 11:53:14.242355

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "40da687f0d4d"
down_revision: Union[str, Sequence[str], None] = "ea167a6ca3c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create api_scopes table for dynamic permission management."""
    op.create_table(
        "api_scopes",
        sa.Column("id", sa.UUID(), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("platform", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_system", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    # Create indexes
    op.create_index("ix_api_scopes_name", "api_scopes", ["name"], unique=False)
    op.create_index("ix_api_scopes_platform", "api_scopes", ["platform"], unique=False)
    op.create_index("ix_api_scopes_category", "api_scopes", ["category"], unique=False)
    op.create_index(
        "ix_api_scopes_organization_id", "api_scopes", ["organization_id"], unique=False
    )

    # Create unique constraint on name + organization_id (same scope name per org)
    op.create_unique_constraint("uq_api_scopes_name_org", "api_scopes", ["name", "organization_id"])


def downgrade() -> None:
    """Drop api_scopes table."""
    op.drop_constraint("uq_api_scopes_name_org", "api_scopes", type_="unique")
    op.drop_index("ix_api_scopes_organization_id", "api_scopes")
    op.drop_index("ix_api_scopes_category", "api_scopes")
    op.drop_index("ix_api_scopes_platform", "api_scopes")
    op.drop_index("ix_api_scopes_name", "api_scopes")
    op.drop_table("api_scopes")
