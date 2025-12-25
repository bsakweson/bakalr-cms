#!/usr/bin/env python3
"""
Map uploaded media to products based on SKU patterns.

This script matches media files to products by analyzing filename patterns
and product SKUs, then updates the seed file with the correct media_ids.
"""
import getpass
import json
import os
import re
import httpx
from collections import defaultdict

API_URL = os.getenv("SEED_API_URL", "http://localhost:8000/api/v1")


def normalize_sku(sku: str) -> str:
    """Normalize SKU for matching (uppercase, remove special chars)."""
    return re.sub(r'[^A-Z0-9]', '', sku.upper())


def extract_sku_from_filename(filename: str) -> str:
    """Extract SKU pattern from filename."""
    # Remove extension
    name = re.sub(r'\.(png|jpg|jpeg|webp|gif)$', '', filename.lower())
    # Split by common delimiters and take meaningful parts
    parts = re.split(r'[-_]', name)
    
    # Try to reconstruct SKU (usually first 2-4 parts)
    if len(parts) >= 2:
        # Check if it looks like a SKU pattern
        return '-'.join(parts[:3]).upper() if len(parts) >= 3 else '-'.join(parts[:2]).upper()
    return name.upper()


def get_media_from_api(client: httpx.Client, headers: dict) -> list:
    """Fetch all media from the CMS API with proper pagination."""
    all_media = []
    page = 1
    total_pages = 1
    
    while page <= total_pages:
        resp = client.get(
            f"{API_URL}/media",
            params={"page": page, "page_size": 100},
            headers=headers
        )
        if resp.status_code != 200:
            print(f"Error fetching page {page}: {resp.status_code}")
            break
        data = resp.json()
        items = data.get("items", [])
        total_pages = data.get("total_pages", 1)
        
        all_media.extend(items)
        print(f"  Page {page}/{total_pages}: {len(items)} items")
        
        if not items:
            break
        page += 1
    
    return all_media


def build_media_index(media_items: list) -> dict:
    """Build an index of media by various key patterns."""
    index = defaultdict(list)
    
    for m in media_items:
        media_id = m.get("id")
        filename = m.get("original_filename", "")
        
        # Index by full filename (without extension)
        base_name = re.sub(r'\.(png|jpg|jpeg|webp|gif)$', '', filename.lower())
        index[base_name].append(media_id)
        
        # Index by SKU prefix patterns
        parts = re.split(r'[-_]', base_name)
        
        # Try different prefix lengths
        for i in range(2, min(5, len(parts) + 1)):
            prefix = '-'.join(parts[:i])
            index[prefix].append(media_id)
    
    return index


def find_media_for_product(sku: str, name: str, media_index: dict, media_items: list) -> list:
    """Find matching media for a product based on SKU and name."""
    matches = set()
    
    # Normalize SKU
    sku_normalized = sku.lower().replace('_', '-')
    sku_parts = sku_normalized.split('-')
    
    # Try exact SKU match
    if sku_normalized in media_index:
        matches.update(media_index[sku_normalized])
    
    # Try SKU prefix matches
    for i in range(len(sku_parts), 1, -1):
        prefix = '-'.join(sku_parts[:i])
        if prefix in media_index:
            matches.update(media_index[prefix])
            if matches:
                break
    
    # Try matching by searching filenames
    if not matches:
        for m in media_items:
            filename = m.get("original_filename", "").lower()
            # Check if SKU appears in filename
            if sku_normalized.replace('-', '') in filename.replace('-', '').replace('_', ''):
                matches.add(m.get("id"))
    
    return list(matches)


def sort_media_ids(media_ids: list, media_items: list) -> list:
    """Sort media IDs so primary image (with -01 or front) comes first."""
    media_map = {m["id"]: m for m in media_items}
    
    def sort_key(mid):
        m = media_map.get(mid, {})
        filename = m.get("original_filename", "").lower()
        # Primary indicators: -01, front, main, primary
        if "-01" in filename or "front" in filename or "main" in filename:
            return 0
        elif "-02" in filename:
            return 1
        elif "-03" in filename:
            return 2
        elif "-04" in filename:
            return 3
        return 10
    
    return sorted(media_ids, key=sort_key)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Map uploaded media to products")
    parser.add_argument("--seed-file", default="seeds/sample-data/11-products.json")
    parser.add_argument("--execute", action="store_true", help="Actually update the seed file")
    args = parser.parse_args()
    
    dry_run = not args.execute
    
    if dry_run:
        print("=" * 60)
        print("DRY RUN MODE - No changes will be made")
        print("Use --execute to actually update the seed file")
        print("=" * 60)
    
    # Authenticate
    email = os.getenv("SEED_ADMIN_EMAIL") or input("Admin email: ").strip()
    password = os.getenv("SEED_ADMIN_PASSWORD") or getpass.getpass("Admin password: ")
    
    client = httpx.Client(timeout=30)
    resp = client.post(f"{API_URL}/auth/login", json={"email": email, "password": password})
    if resp.status_code != 200:
        print(f"Auth failed: {resp.json().get('detail')}")
        return
    
    token = resp.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print(f"✓ Authenticated as {email}\n")
    
    # Get all media
    print("Fetching media from CMS...")
    media_items = get_media_from_api(client, headers)
    print(f"Found {len(media_items)} media items\n")
    
    if not media_items:
        print("No media found in CMS. Upload media first.")
        return
    
    # Build media index
    media_index = build_media_index(media_items)
    
    # Load seed file
    with open(args.seed_file) as f:
        products = json.load(f)
    
    print("=" * 60)
    print("MAPPING MEDIA TO PRODUCTS")
    print("=" * 60)
    
    mapped = 0
    already_mapped = 0
    no_match = []
    
    for product in products:
        data = product.get("content_data", {})
        sku = data.get("sku", "")
        name = data.get("name", product.get("slug", ""))
        current_media = data.get("media_ids", [])
        
        # Skip if already has media
        if current_media:
            already_mapped += 1
            continue
        
        # Find matching media
        matching_ids = find_media_for_product(sku, name, media_index, media_items)
        
        if matching_ids:
            # Sort so primary image is first
            sorted_ids = sort_media_ids(matching_ids, media_items)
            data["media_ids"] = sorted_ids
            mapped += 1
            
            # Get filenames for display
            filenames = []
            for mid in sorted_ids:
                for m in media_items:
                    if m["id"] == mid:
                        filenames.append(m.get("original_filename", mid[:8]))
                        break
            
            print(f"✓ {sku}: {len(sorted_ids)} images")
            for fn in filenames:
                print(f"    - {fn}")
        else:
            no_match.append((sku, name))
    
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Already mapped:  {already_mapped}")
    print(f"Newly mapped:    {mapped}")
    print(f"No match found:  {len(no_match)}")
    
    if no_match:
        print(f"\nProducts without matching media ({len(no_match)}):")
        for sku, name in no_match:
            print(f"  - {sku}: {name}")
    
    if not dry_run and mapped > 0:
        with open(args.seed_file, "w") as f:
            json.dump(products, f, indent=2)
        print(f"\n✓ Updated {args.seed_file}")
    elif dry_run and mapped > 0:
        print(f"\nRun with --execute to save changes")


if __name__ == "__main__":
    main()
