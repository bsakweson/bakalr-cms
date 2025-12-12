#!/usr/bin/env python3
"""
Migrate product specifications from dict format to array format.

Before: {"Hair Type": "Brazilian", "Origin": "Brazil"}
After:  [{"label": "Hair Type", "value": "Brazilian"}, {"label": "Origin", "value": "Brazil"}]

This allows both keys and values to be translated by the translation service.
"""
import os
import sys

# Add backend to path
sys.path.insert(0, "/app")
os.chdir("/app")

from backend.db.session import SessionLocal
from backend.models.content import ContentEntry, ContentType


def migrate_specifications():
    """Convert specifications from dict to array format."""
    db = SessionLocal()

    try:
        # Get product content type
        product_type = db.query(ContentType).filter(ContentType.api_id == "product").first()

        if not product_type:
            print("Product content type not found!")
            return

        print(f"Found product content type: {product_type.id}")

        # Get all products
        products = (
            db.query(ContentEntry).filter(ContentEntry.content_type_id == product_type.id).all()
        )

        print(f"Found {len(products)} products to migrate")

        migrated = 0
        skipped = 0

        for product in products:
            data = dict(product.data) if product.data else {}
            specs = data.get("specifications")

            if specs is None:
                print(f"  [{product.slug}] No specifications - skipping")
                skipped += 1
                continue

            # Check if already migrated (is a list)
            if isinstance(specs, list):
                print(f"  [{product.slug}] Already migrated - skipping")
                skipped += 1
                continue

            # Convert dict to array format
            if isinstance(specs, dict):
                new_specs = [{"label": key, "value": value} for key, value in specs.items()]

                # Update the data
                data["specifications"] = new_specs
                product.data = data

                print(f"  [{product.slug}] Migrated {len(new_specs)} specs")
                migrated += 1

        # Commit all changes
        db.commit()

        print("\n✅ Migration complete!")
        print(f"   Migrated: {migrated}")
        print(f"   Skipped:  {skipped}")

    finally:
        db.close()


if __name__ == "__main__":
    migrate_specifications()
