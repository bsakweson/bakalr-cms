"""rename_permissions_to_dot_notation

Revision ID: 5b42fd906a78
Revises: c4f0a4a027ee
Create Date: 2025-12-21 06:58:44.302794

Renames underscore-style permissions to consistent dot notation:
- content_type.* -> content.type.*
- api_key.* -> api.key.*
- audit_log.* -> audit.log.*
- manage_roles -> role.manage
- view_roles -> role.view
- roles.manage -> role.manage
- themes.manage -> theme.manage
- users.manage -> user.manage.full
- view_audit_logs -> audit.logs
- manage_organization_settings -> organization.settings.manage
- view_organization_settings -> organization.settings.view
- notifications.* -> notification.*
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5b42fd906a78"
down_revision: Union[str, Sequence[str], None] = "c4f0a4a027ee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Permission rename mapping: old_name -> new_name
PERMISSION_RENAMES = {
    # Content type permissions
    "content_type.read": "content.type.read",
    "content_type.create": "content.type.create",
    "content_type.update": "content.type.update",
    "content_type.delete": "content.type.delete",
    # API key permissions
    "api_key.read": "api.key.read",
    "api_key.create": "api.key.create",
    "api_key.delete": "api.key.delete",
    # Audit permissions
    "audit_log.read": "audit.log.read",
    "view_audit_logs": "audit.logs",
    # Role permissions
    "manage_roles": "role.manage",
    "view_roles": "role.view",
    "roles.manage": "role.manage",
    # Theme permissions
    "themes.manage": "theme.manage",
    # User permissions
    "users.manage": "user.manage.full",
    # Organization permissions
    "manage_organization_settings": "organization.settings.manage",
    "view_organization_settings": "organization.settings.view",
    # Notification permissions
    "notifications.view": "notification.view",
    "notifications.create": "notification.create",
}


def upgrade() -> None:
    """Rename underscore permissions to dot notation."""
    connection = op.get_bind()

    for old_name, new_name in PERMISSION_RENAMES.items():
        # Check if old permission exists
        result = connection.execute(
            sa.text("SELECT id FROM permissions WHERE name = :name"), {"name": old_name}
        ).fetchone()

        if result:
            old_id = result[0]

            # Check if new permission already exists
            new_result = connection.execute(
                sa.text("SELECT id FROM permissions WHERE name = :name"), {"name": new_name}
            ).fetchone()

            if new_result:
                new_id = new_result[0]
                # New permission exists - migrate role_permissions and delete old
                print(f"  Migrating {old_name} (id={old_id}) -> {new_name} (id={new_id})")

                # Update role_permissions to point to new permission (ignore duplicates)
                connection.execute(
                    sa.text(
                        """
                        UPDATE role_permissions
                        SET permission_id = :new_id
                        WHERE permission_id = :old_id
                        AND role_id NOT IN (
                            SELECT role_id FROM role_permissions WHERE permission_id = :new_id
                        )
                    """
                    ),
                    {"old_id": old_id, "new_id": new_id},
                )

                # Delete remaining role_permissions for old permission (duplicates)
                connection.execute(
                    sa.text("DELETE FROM role_permissions WHERE permission_id = :old_id"),
                    {"old_id": old_id},
                )

                # Delete old permission
                connection.execute(
                    sa.text("DELETE FROM permissions WHERE id = :id"), {"id": old_id}
                )
            else:
                # New permission doesn't exist - just rename
                print(f"  Renaming {old_name} -> {new_name}")
                connection.execute(
                    sa.text("UPDATE permissions SET name = :new_name WHERE id = :id"),
                    {"new_name": new_name, "id": old_id},
                )
        else:
            print(f"  Skipping {old_name} (not found in DB)")


def downgrade() -> None:
    """Revert dot notation permissions back to underscore style."""
    connection = op.get_bind()

    # Reverse the mapping
    for old_name, new_name in PERMISSION_RENAMES.items():
        result = connection.execute(
            sa.text("SELECT id FROM permissions WHERE name = :name"), {"name": new_name}
        ).fetchone()

        if result:
            print(f"  Reverting {new_name} -> {old_name}")
            connection.execute(
                sa.text("UPDATE permissions SET name = :old_name WHERE id = :id"),
                {"old_name": old_name, "id": result[0]},
            )
