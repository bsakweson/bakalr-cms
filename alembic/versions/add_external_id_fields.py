"""add external identity provider fields

Revision ID: add_external_id_fields
Revises:
Create Date: 2025-01-08

Adds external_id and external_provider fields to users and organizations
tables to support external identity providers (Keycloak, etc.)
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_external_id_fields"
down_revision: Union[str, None] = None  # Will be set automatically
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add external_id and external_provider to users table
    op.add_column("users", sa.Column("external_id", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("external_provider", sa.String(50), nullable=True))
    op.create_index("ix_users_external_id", "users", ["external_id"], unique=True)

    # Add external_id and external_provider to organizations table
    op.add_column("organizations", sa.Column("external_id", sa.String(255), nullable=True))
    op.add_column("organizations", sa.Column("external_provider", sa.String(50), nullable=True))
    op.create_index("ix_organizations_external_id", "organizations", ["external_id"], unique=True)


def downgrade() -> None:
    # Remove from organizations
    op.drop_index("ix_organizations_external_id", table_name="organizations")
    op.drop_column("organizations", "external_provider")
    op.drop_column("organizations", "external_id")

    # Remove from users
    op.drop_index("ix_users_external_id", table_name="users")
    op.drop_column("users", "external_provider")
    op.drop_column("users", "external_id")
