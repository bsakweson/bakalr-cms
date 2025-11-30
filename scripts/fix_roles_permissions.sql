-- Add missing role management permissions
INSERT INTO permissions (name, description, category, created_at, updated_at)
VALUES
    ('manage_roles', 'Can create, update, and delete roles', 'role_management', NOW(), NOW()),
    ('view_roles', 'Can view roles and their permissions', 'role_management', NOW(), NOW())
ON CONFLICT (name) DO NOTHING;

-- Get the permission IDs we just created
DO $$
DECLARE
    manage_roles_id INTEGER;
    view_roles_id INTEGER;
    admin_role_id INTEGER;
BEGIN
    -- Get permission IDs
    SELECT id INTO manage_roles_id FROM permissions WHERE name = 'manage_roles';
    SELECT id INTO view_roles_id FROM permissions WHERE name = 'view_roles';

    -- Assign to all admin roles in all organizations
    FOR admin_role_id IN
        SELECT id FROM roles WHERE name = 'admin'
    LOOP
        -- Add manage_roles permission
        INSERT INTO role_permissions (role_id, permission_id)
        VALUES (admin_role_id, manage_roles_id)
        ON CONFLICT (role_id, permission_id) DO NOTHING;

        -- Add view_roles permission
        INSERT INTO role_permissions (role_id, permission_id)
        VALUES (admin_role_id, view_roles_id)
        ON CONFLICT (role_id, permission_id) DO NOTHING;
    END LOOP;

    RAISE NOTICE 'Successfully added role management permissions to admin roles';
END $$;
