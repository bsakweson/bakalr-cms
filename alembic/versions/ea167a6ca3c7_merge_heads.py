"""merge heads

Revision ID: ea167a6ca3c7
Revises: add_external_id_fields, f5938gc613d2
Create Date: 2025-12-10 17:53:20.761021

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "ea167a6ca3c7"
down_revision: Union[str, Sequence[str], None] = ("add_external_id_fields", "f5938gc613d2")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
