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
    # Columns already exist from partial migration, just add FK
    # Check if columns exist before adding them
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('permissions')]
    
    with op.batch_alter_table('permissions', schema=None, recreate='always') as batch_op:
        # Only add columns if they don't exist
        if 'content_type_id' not in columns:
            batch_op.add_column(sa.Column('content_type_id', sa.Integer(), nullable=True))
        if 'field_name' not in columns:
            batch_op.add_column(sa.Column('field_name', sa.String(length=100), nullable=True))
        
        # Add indexes if they don't exist
        indexes = [idx['name'] for idx in inspector.get_indexes('permissions')]
        if 'ix_permissions_content_type_id' not in indexes:
            batch_op.create_index('ix_permissions_content_type_id', ['content_type_id'], unique=False)
        if 'ix_permissions_field_name' not in indexes:
            batch_op.create_index('ix_permissions_field_name', ['field_name'], unique=False)
        
        # Add FK constraint
        batch_op.create_foreign_key('fk_permissions_content_type', 'content_types', ['content_type_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    """Downgrade schema."""
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table('permissions', schema=None, recreate='always') as batch_op:
        batch_op.drop_constraint('fk_permissions_content_type', type_='foreignkey')
        batch_op.drop_index('ix_permissions_field_name')
        batch_op.drop_index('ix_permissions_content_type_id')
        batch_op.drop_column('field_name')
        batch_op.drop_column('content_type_id')
