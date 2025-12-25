#!/usr/bin/env python3
"""
Migrate product images from legacy format to best-practice media format.

Legacy format (type: json):
  "images": [
    {"url": "...", "alt_text": "...", "is_primary": true, "media_id": "...", "cms_url": "..."},
    ...
  ]

New format (type: media + json):
  "primary_image_id": "uuid-of-primary-image",
  "gallery_image_ids": ["uuid-1", "uuid-2", ...],
  "images": [...] // kept for backward compatibility
"""
import json
import sys
from pathlib import Path

SEED_FILE = "seeds/sample-data/11-products.json"
BACKUP_FILE = "seeds/sample-data/11-products.json.backup"


def migrate_product(product: dict) -> dict:
    """Migrate a single product's image structure."""
    content = product.get("content_data", {})
    images = content.get("images", [])

    if not images:
        return product

    # Find primary image
    primary_image = None
    gallery_images = []

    for img in images:
        media_id = img.get("media_id")
        if not media_id:
            continue

        if img.get("is_primary"):
            primary_image = media_id
        else:
            gallery_images.append(media_id)

    # If no primary explicitly set, use the first image
    if not primary_image and images:
        first_with_media = next((img for img in images if img.get("media_id")), None)
        if first_with_media:
            primary_image = first_with_media.get("media_id")
            # Remove from gallery if it was added there
            if primary_image in gallery_images:
                gallery_images.remove(primary_image)

    # Update content_data with new fields
    if primary_image:
        content["primary_image_id"] = primary_image

    if gallery_images:
        content["gallery_image_ids"] = gallery_images

    # Keep legacy images field for backward compatibility
    product["content_data"] = content
    return product


def main():
    # Load products
    seed_path = Path(SEED_FILE)
    if not seed_path.exists():
        print(f"Error: {SEED_FILE} not found")
        sys.exit(1)

    with open(seed_path) as f:
        products = json.load(f)

    print(f"Loaded {len(products)} products")

    # Create backup
    backup_path = Path(BACKUP_FILE)
    with open(backup_path, "w") as f:
        json.dump(products, f, indent=2)
    print(f"✓ Created backup at {BACKUP_FILE}")

    # Migrate each product
    migrated_count = 0
    already_migrated = 0
    no_images = 0

    for product in products:
        content = product.get("content_data", {})

        # Check if already migrated
        if content.get("primary_image_id"):
            already_migrated += 1
            continue

        # Check if has images to migrate
        images = content.get("images", [])
        if not images:
            no_images += 1
            continue

        # Check if any images have media_id
        has_media = any(img.get("media_id") for img in images)
        if not has_media:
            no_images += 1
            continue

        migrate_product(product)
        migrated_count += 1

    # Save updated products
    with open(seed_path, "w") as f:
        json.dump(products, f, indent=2)

    print()
    print("=== MIGRATION SUMMARY ===")
    print(f"Total products:     {len(products)}")
    print(f"Migrated:           {migrated_count}")
    print(f"Already migrated:   {already_migrated}")
    print(f"No images/media:    {no_images}")
    print()
    print(f"✓ Updated {SEED_FILE}")

    # Show sample of migrated data
    print()
    print("=== SAMPLE MIGRATED PRODUCT ===")
    for product in products:
        content = product.get("content_data", {})
        if content.get("primary_image_id"):
            print(f"Product: {content.get('name', product.get('slug'))}")
            print(f"  primary_image_id: {content.get('primary_image_id')}")
            print(f"  gallery_image_ids: {content.get('gallery_image_ids', [])[:3]}...")
            print(f"  legacy images count: {len(content.get('images', []))}")
            break


if __name__ == "__main__":
    main()
