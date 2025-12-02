#!/usr/bin/env python
"""Grant themes.manage permission to user."""

from backend.db.session import SessionLocal
from backend.models.user import User
from backend.models.rbac import Role, Permission

db = SessionLocal()

# Get user
user = db.query(User).filter(User.email == 'bsakweson@gmail.com').first()
if not user:
    print("User not found")
    exit(1)

print(f"User: {user.email}, Org: {user.organization_id}")

# Check if themes.manage permission exists
perm = db.query(Permission).filter(
    Permission.name == 'themes.manage',
    Permission.organization_id == user.organization_id
).first()

if not perm:
    print("Creating themes.manage permission...")
    perm = Permission(
        name='themes.manage',
        description='Manage organization themes',
        resource='themes',
        action='manage',
        organization_id=user.organization_id
    )
    db.add(perm)
    db.commit()
    print("✅ Permission created!")
else:
    print(f"✅ Permission exists: {perm.name}")

# Get admin role for this org
admin_role = db.query(Role).filter(
    Role.name == 'admin',
    Role.organization_id == user.organization_id
).first()

if admin_role:
    # Add permission to admin role if not already there
    if perm not in admin_role.permissions:
        admin_role.permissions.append(perm)
        db.commit()
        print(f"✅ Added themes.manage to admin role")
    else:
        print("✅ Admin role already has themes.manage")
    
    # Check if user has admin role
    if admin_role not in user.roles:
        user.roles.append(admin_role)
        db.commit()
        print(f"✅ Added admin role to user")
    else:
        print("✅ User already has admin role")
else:
    print("❌ Admin role not found")

db.close()
print("\n🎉 Done! User now has themes.manage permission")
