"""Add email verification fields

Revision ID: add_email_verification
Revises:
Create Date: 2025-11-29

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_email_verification"
down_revision = "6f8704939c05"  # Parent before the branch
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add email_verification_token and email_verification_expires columns
    # Remove old verification_token column if it exists
    op.execute(
        """
        ALTER TABLE users
        DROP COLUMN IF EXISTS verification_token
    """
    )

    op.add_column(
        "users", sa.Column("email_verification_token", sa.String(length=255), nullable=True)
    )
    op.add_column("users", sa.Column("email_verification_expires", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "email_verification_expires")
    op.drop_column("users", "email_verification_token")
