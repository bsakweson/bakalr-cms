"""add_owner_id_to_organizations

Revision ID: 46d4a7843fa6
Revises: b27b4dddb9ea
Create Date: 2025-11-30 19:18:29.453547

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "46d4a7843fa6"
down_revision: Union[str, Sequence[str], None] = "b27b4dddb9ea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add owner_id column (nullable)
    op.add_column("organizations", sa.Column("owner_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_organizations_owner_id"), "organizations", ["owner_id"], unique=False)
    op.create_foreign_key(
        "fk_organizations_owner_id",
        "organizations",
        "users",
        ["owner_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # Backfill existing organizations with first admin as owner
    # This SQL finds the first admin user created for each organization
    op.execute(
        """
        UPDATE organizations o
        SET owner_id = (
            SELECT u.id
            FROM users u
            JOIN user_organizations uo ON u.id = uo.user_id
            JOIN user_roles ur ON u.id = ur.user_id
            JOIN roles r ON ur.role_id = r.id
            WHERE uo.organization_id = o.id
            AND r.name = 'Admin'
            AND r.organization_id = o.id
            ORDER BY u.created_at ASC
            LIMIT 1
        )
        WHERE o.owner_id IS NULL
    """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_organizations_owner_id", "organizations", type_="foreignkey")
    op.drop_index(op.f("ix_organizations_owner_id"), table_name="organizations")
    op.drop_column("organizations", "owner_id")
