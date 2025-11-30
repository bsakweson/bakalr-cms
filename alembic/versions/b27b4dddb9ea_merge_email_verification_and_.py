"""merge email verification and notifications

Revision ID: b27b4dddb9ea
Revises: add_email_verification, add_notifications_email
Create Date: 2025-11-29 23:06:21.291623

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "b27b4dddb9ea"
down_revision: Union[str, Sequence[str], None] = (
    "add_email_verification",
    "add_notifications_email",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
