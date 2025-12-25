#!/usr/bin/env python3
"""Show product image migration status"""
import json

with open("seeds/sample-data/11-products.json") as f:
    products = json.load(f)

print("=== PRODUCT IMAGE STATUS AFTER MIGRATION ===")
print()
print(f"{'SKU':<22} {'NAME':<35} {'PRI':<5} {'GAL':<5} {'LEG':<5} STATUS")
print("-" * 90)

for p in sorted(products, key=lambda x: x.get("content_data", {}).get("sku", "")):
    content = p.get("content_data", {})
    sku = content.get("sku", "N/A")
    name = content.get("name", "")[:32]

    primary = content.get("primary_image_id")
    gallery = content.get("gallery_image_ids", [])
    images = content.get("images", [])

    pri = "✓" if primary else "-"
    gal = len(gallery) if gallery else "-"
    leg = len(images) if images else "-"

    if primary:
        status = "✅ Migrated"
    elif images and any(img.get("media_id") for img in images):
        status = "⚠️ Has media_id but not migrated"
    elif images:
        status = "📤 Needs upload"
    else:
        status = "❌ No images"

    print(f"{sku:<22} {name:<35} {str(pri):<5} {str(gal):<5} {str(leg):<5} {status}")

print()
print("=== SUMMARY ===")
migrated = sum(1 for p in products if p.get("content_data", {}).get("primary_image_id"))
needs_upload = sum(
    1
    for p in products
    if p.get("content_data", {}).get("images")
    and not p.get("content_data", {}).get("primary_image_id")
)
no_images = sum(1 for p in products if not p.get("content_data", {}).get("images"))

print(f"✅ Migrated (has primary_image_id): {migrated}")
print(f"📤 Needs media upload:              {needs_upload}")
print(f"❌ No images at all:                {no_images}")
