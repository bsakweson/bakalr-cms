#!/usr/bin/env python3
"""
Migrate product media from legacy fields to consolidated media_ids field.

Best Practice: Products should use a single 'media_ids' field (array of UUIDs)
where the first item is the primary image and remaining items are gallery images.

Legacy fields being deprecated:
- primary_image_id: single media ID
- gallery_image_ids: array of media IDs
- images: array of objects with {url, alt_text, is_primary, media_id, cms_url}

New format:
- media_ids: array of UUID strings, e.g., ["uuid1", "uuid2", "uuid3"]
"""
import getpass
import json
import os
import sys
import httpx

API_URL = os.getenv("SEED_API_URL", "http://localhost:8000/api/v1")


def extract_media_ids_from_product(data: dict) -> list:
    """
    Extract media IDs from legacy fields and consolidate into single array.
    First item is primary image, rest are gallery images.
    """
    media_ids = []
    
    # Check for legacy 'images' array with media_id
    images = data.get("images", [])
    if images:
        primary_id = None
        gallery_ids = []
        
        for img in images:
            if isinstance(img, dict):
                media_id = img.get("media_id")
                if media_id:
                    if img.get("is_primary"):
                        primary_id = media_id
                    else:
                        gallery_ids.append(media_id)
        
        # Primary first, then gallery
        if primary_id:
            media_ids.append(primary_id)
        media_ids.extend(gallery_ids)
    
    # Check for primary_image_id (single ID)
    if not media_ids:
        primary_id = data.get("primary_image_id")
        if primary_id:
            media_ids.append(primary_id)
        
        # Add gallery_image_ids
        gallery_ids = data.get("gallery_image_ids", [])
        if gallery_ids:
            media_ids.extend(gallery_ids)
    
    # Deduplicate while preserving order
    seen = set()
    unique_ids = []
    for mid in media_ids:
        if mid and mid not in seen:
            seen.add(mid)
            unique_ids.append(mid)
    
    return unique_ids


def has_legacy_image_fields(data: dict) -> bool:
    """Check if product has any legacy image fields that should be cleaned up."""
    # Check for non-empty legacy fields only
    images = data.get("images")
    if images and len(images) > 0:
        return True
    if data.get("primary_image_id"):
        return True
    gallery = data.get("gallery_image_ids")
    if gallery and len(gallery) > 0:
        return True
    if data.get("image_url") or data.get("main_image"):
        return True
    return False


def migrate_database_products(client: httpx.Client, headers: dict, dry_run: bool = True, clean_legacy: bool = False):
    """Migrate products in the database."""
    print(f"\n{'[DRY RUN] ' if dry_run else ''}=== MIGRATING DATABASE PRODUCTS ===")
    
    # Get all products
    resp = client.get(
        f"{API_URL}/content/entries",
        params={"content_type_slug": "product", "page_size": 200},
        headers=headers
    )
    
    if resp.status_code != 200:
        print(f"Failed to fetch products: {resp.status_code}")
        return
    
    products = resp.json().get("items", [])
    print(f"Found {len(products)} products to process")
    
    migrated = 0
    cleaned = 0
    already_done = 0
    no_media = 0
    errors = 0
    
    for product in products:
        product_id = product.get("id")
        slug = product.get("slug")
        data = product.get("data", {})
        
        # Check if already migrated (has media_ids)
        if data.get("media_ids"):
            already_done += 1
            continue
        
        # Extract media IDs from legacy fields
        media_ids = extract_media_ids_from_product(data)
        
        if not media_ids:
            no_media += 1
            continue
        
        # Prepare update
        new_data = {
            "media_ids": media_ids,
            # Remove legacy fields
            "primary_image_id": None,
            "gallery_image_ids": None,
            "images": None,
        }
        
        if dry_run:
            print(f"  Would update {slug}: {len(media_ids)} media IDs")
            migrated += 1
        else:
            # Update product
            update_resp = client.patch(
                f"{API_URL}/content/entries/{product_id}",
                json={"data": new_data},
                headers=headers
            )
            
            if update_resp.status_code == 200:
                print(f"  ✓ Migrated {slug}: {len(media_ids)} media IDs")
                migrated += 1
            else:
                print(f"  ✗ Failed {slug}: {update_resp.status_code}")
                errors += 1
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Migration Summary:")
    print(f"  Migrated:      {migrated}")
    print(f"  Already done:  {already_done}")
    print(f"  No media:      {no_media}")
    if errors:
        print(f"  Errors:        {errors}")


def migrate_seed_file(input_path: str, output_path: str = None, dry_run: bool = True):
    """Migrate a seed file to use media_ids format."""
    if output_path is None:
        output_path = input_path
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}=== MIGRATING SEED FILE ===")
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    
    with open(input_path, "r") as f:
        products = json.load(f)
    
    migrated = 0
    already_done = 0
    no_media = 0
    cleaned_legacy = 0
    
    for product in products:
        data = product.get("content_data", {})
        
        # Check if already migrated
        if data.get("media_ids"):
            already_done += 1
            continue
        
        # Extract media IDs
        media_ids = extract_media_ids_from_product(data)
        
        if not media_ids:
            # Check if we should clean up legacy fields without media IDs
            # (URL-only images that haven't been uploaded to media library)
            if has_legacy_image_fields(data):
                # Remove legacy fields (images need to be uploaded separately)
                data.pop("primary_image_id", None)
                data.pop("gallery_image_ids", None)
                data.pop("images", None)
                data.pop("image_url", None)
                data.pop("main_image", None)
                # Initialize empty media_ids
                data["media_ids"] = []
                cleaned_legacy += 1
            else:
                no_media += 1
            continue
        
        # Update content_data
        data["media_ids"] = media_ids
        
        # Remove legacy fields
        data.pop("primary_image_id", None)
        data.pop("gallery_image_ids", None)
        data.pop("images", None)
        
        migrated += 1
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Seed File Summary:")
    print(f"  Migrated:        {migrated}")
    print(f"  Cleaned legacy:  {cleaned_legacy} (had URL-only images, need upload)")
    print(f"  Already done:    {already_done}")
    print(f"  No media:        {no_media}")
    
    if not dry_run and (migrated > 0 or cleaned_legacy > 0):
        with open(output_path, "w") as f:
            json.dump(products, f, indent=2)
        print(f"\n✓ Saved to {output_path}")
    
    return products


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate product media to consolidated media_ids field"
    )
    parser.add_argument(
        "--mode",
        choices=["database", "seed", "both"],
        default="both",
        help="Migration mode: database, seed file, or both"
    )
    parser.add_argument(
        "--seed-file",
        default="seeds/sample-data/11-products.json",
        help="Path to seed file (default: seeds/sample-data/11-products.json)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform the migration (required to make changes)"
    )
    
    args = parser.parse_args()
    
    # Require explicit --execute to make changes
    dry_run = not args.execute
    
    if dry_run:
        print("=" * 60)
        print("DRY RUN MODE - No changes will be made")
        print("Use --execute to actually perform the migration")
        print("=" * 60)
    
    if args.mode in ("seed", "both"):
        migrate_seed_file(args.seed_file, dry_run=dry_run)
    
    if args.mode in ("database", "both"):
        # Authenticate
        email = os.getenv("SEED_ADMIN_EMAIL") or input("Admin email: ").strip()
        password = os.getenv("SEED_ADMIN_PASSWORD") or getpass.getpass("Admin password: ")
        
        client = httpx.Client(timeout=30)
        login_resp = client.post(
            f"{API_URL}/auth/login",
            json={"email": email, "password": password}
        )
        
        if login_resp.status_code != 200:
            print(f"Authentication failed: {login_resp.json().get('detail')}")
            sys.exit(1)
        
        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        print(f"✓ Authenticated as {email}")
        
        migrate_database_products(client, headers, dry_run=dry_run)
    
    if dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN COMPLETE - Run with --execute to apply changes")
        print("=" * 60)


if __name__ == "__main__":
    main()
