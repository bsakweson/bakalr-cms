"""add_field_level_permissions

Revision ID: 7b84c92e8d55
Revises: 69c20a9ee9a7
Create Date: 2025-11-24 21:29:59.177755

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b84c92e8d55'
down_revision: Union[str, Sequence[str], None] = '69c20a9ee9a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add columns to permissions table for field-level permissions
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('permissions')]
    
    # Add columns if they don't exist
    if 'content_type_id' not in columns:
        op.add_column('permissions', sa.Column('content_type_id', sa.Integer(), nullable=True))
    if 'field_name' not in columns:
        op.add_column('permissions', sa.Column('field_name', sa.String(length=100), nullable=True))
    
    # Add indexes if they don't exist
    indexes = [idx['name'] for idx in inspector.get_indexes('permissions')]
    if 'ix_permissions_content_type_id' not in indexes:
        op.create_index('ix_permissions_content_type_id', 'permissions', ['content_type_id'], unique=False)
    if 'ix_permissions_field_name' not in indexes:
        op.create_index('ix_permissions_field_name', 'permissions', ['field_name'], unique=False)
    
    # Add FK constraint
    op.create_foreign_key('fk_permissions_content_type', 'permissions', 'content_types', ['content_type_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    """Downgrade schema."""
    # Remove FK and columns
    op.drop_constraint('fk_permissions_content_type', 'permissions', type_='foreignkey')
    op.drop_index('ix_permissions_field_name', table_name='permissions')
    op.drop_index('ix_permissions_content_type_id', table_name='permissions')
    op.drop_column('permissions', 'field_name')
    op.drop_column('permissions', 'content_type_id')
