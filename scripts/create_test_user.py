#!/usr/bin/env python3
"""Create a test admin user for development"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session

from backend.core.security import get_password_hash
from backend.db.session import SessionLocal
from backend.models.organization import Organization
from backend.models.rbac import Role
from backend.models.user import User


def create_test_user():
    db: Session = SessionLocal()

    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == "admin@example.com").first()
        if existing_user:
            print("✅ Admin user already exists!")
            print("   Email: admin@example.com")
            print("   Password: admin123")
            print(f"   Organization: {existing_user.organization.name}")
            return

        # Check if organization exists
        org = db.query(Organization).filter(Organization.slug == "bakalr-demo").first()
        if not org:
            # Create organization
            org = Organization(name="Bakalr Demo", slug="bakalr-demo", settings={})
            db.add(org)
            db.flush()
            print(f"✅ Created organization: {org.name}")

        # Create admin role if it doesn't exist
        admin_role = (
            db.query(Role).filter(Role.name == "admin", Role.organization_id == org.id).first()
        )

        if not admin_role:
            admin_role = Role(
                name="admin", description="Administrator with full access", organization_id=org.id
            )
            db.add(admin_role)
            db.flush()
            print("✅ Created admin role")

        # Create user
        user = User(
            email="admin@example.com",
            password_hash=get_password_hash("admin123"),
            full_name="Admin User",
            organization_id=org.id,
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        db.flush()

        # Assign admin role
        user.roles.append(admin_role)

        db.commit()

        print("\n✅ Test admin user created successfully!")
        print("   Email: admin@example.com")
        print("   Password: admin123")
        print(f"   Organization: {org.name}")
        print("\nYou can now log in at: http://localhost:3001/login")

    except Exception as e:
        db.rollback()
        print(f"❌ Error creating user: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_test_user()
