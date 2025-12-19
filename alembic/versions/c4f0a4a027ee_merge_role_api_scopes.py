"""merge role_api_scopes

Revision ID: c4f0a4a027ee
Revises: 40da687f0d4d, 595d9ef40762
Create Date: 2025-12-17 13:16:59.031118

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "c4f0a4a027ee"
down_revision: Union[str, Sequence[str], None] = ("40da687f0d4d", "595d9ef40762")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
