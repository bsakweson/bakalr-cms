#!/usr/bin/env python3
"""
Script to create boutique platform API keys for existing organizations
that don't have one yet.

Run with:
  docker exec bakalr-backend python scripts/create_boutique_api_keys.py

Or pipe it:
  cat scripts/create_boutique_api_keys.py | docker exec -i bakalr-backend python -
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.seed_permissions import create_organization_boutique_api_key
from backend.db.session import SessionLocal
from backend.models.api_key import APIKey
from backend.models.organization import Organization


def create_missing_api_keys():
    """Create boutique API keys for organizations that don't have one."""
    db = SessionLocal()

    try:
        # Get all organizations
        orgs = db.query(Organization).all()
        print(f"Found {len(orgs)} organizations")

        created_keys = []

        for org in orgs:
            print(f"\n=== Processing organization: {org.name} (ID: {org.id}) ===")

            # Check if boutique API key already exists
            existing_key = (
                db.query(APIKey)
                .filter(
                    APIKey.organization_id == org.id,
                    APIKey.name == "Boutique Platform API Key",
                    APIKey.is_active == True,
                )
                .first()
            )

            if existing_key:
                print(f"  ℹ️  API key already exists: {existing_key.key_prefix}...")
                continue

            # Create the API key
            result = create_organization_boutique_api_key(db, org.id)

            if result.get("api_key"):
                created_keys.append(
                    {
                        "organization": org.name,
                        "organization_id": str(org.id),
                        "api_key": result["api_key"],
                        "key_prefix": result["key_prefix"],
                    }
                )

        # Commit all changes
        db.commit()

        # Print summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        if created_keys:
            print(f"\n✅ Created {len(created_keys)} new API keys:\n")
            for key_info in created_keys:
                print(f"Organization: {key_info['organization']}")
                print(f"  ID: {key_info['organization_id']}")
                print(f"  API Key: {key_info['api_key']}")
                print(f"  Prefix: {key_info['key_prefix']}")
                print()

            print("⚠️  IMPORTANT: Save these API keys securely!")
            print("   They will NOT be shown again.")
        else:
            print("\nℹ️  All organizations already have boutique API keys.")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_missing_api_keys()
