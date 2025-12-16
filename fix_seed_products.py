#!/usr/bin/env python3
"""Fix products seed file to use _category_slug and _brand_slug instead of hardcoded UUIDs"""
import json

# Load the products file
with open("seeds/sample-data/11-products.json", "r") as f:
    products = json.load(f)

# Map UUIDs to slugs for categories
category_uuid_to_slug = {
    "aabac525-b1e4-4ec4-89ed-ed34a1de531e": "hair-extensions",
    "f9e023fc-60e6-42f5-b374-ef9629879f5e": "wigs",
    "98173392-35db-40c4-8d63-f9e7b10b5a82": "hair-textures",
    "f4a1a932-c3a2-41fb-a570-72b67a70e469": "hair-care",
    "60fa3f12-c73f-46a0-8e68-cfcfe979b7e4": "tools-accessories",
    "cc0673fa-c51a-4ca5-ad42-2ec68747f645": "braiding-crochet",
    "34cc7674-d87d-4bb8-afe2-44e44a9e55e4": "beauty-cosmetics",
    "8851e5e0-f482-4942-9a6b-71448316d5d9": "protective-styling",
    # Sub-categories
    "vietnamese-hair": "vietnamese-hair",
    "brazilian-hair": "brazilian-hair",
}

# Map UUIDs to slugs for brands (we'll need to figure these out)
brand_uuid_to_slug = {}

# First pass - collect brand_id UUIDs
brand_ids = set()
category_ids = set()
for product in products:
    if "content_data" in product:
        if "brand_id" in product["content_data"]:
            brand_ids.add(product["content_data"]["brand_id"])
        if "category_id" in product["content_data"]:
            category_ids.add(product["content_data"]["category_id"])

print(f"Found {len(category_ids)} unique category_ids:")
for cid in category_ids:
    slug = category_uuid_to_slug.get(cid, "UNKNOWN")
    print(f"  {cid} -> {slug}")

print(f"\nFound {len(brand_ids)} unique brand_ids:")
for bid in brand_ids:
    print(f"  {bid}")

# Update the products - move to _category_slug and _brand_slug
updated = []
cat_count = 0
brand_count = 0

for product in products:
    slug = product.get("slug")

    if "content_data" in product:
        # Handle category_id
        if "category_id" in product["content_data"]:
            cat_id = product["content_data"].pop("category_id")
            cat_slug = category_uuid_to_slug.get(cat_id)
            if cat_slug:
                product["_category_slug"] = cat_slug
                cat_count += 1
            else:
                print(f"WARNING: Unknown category_id {cat_id} for {slug}")

        # Handle brand_id
        if "brand_id" in product["content_data"]:
            brand_id = product["content_data"].pop("brand_id")
            brand_slug = brand_uuid_to_slug.get(brand_id)
            if brand_slug:
                product["_brand_slug"] = brand_slug
                brand_count += 1
            else:
                print(f"WARNING: Unknown brand_id {brand_id} for {slug}")

    updated.append(product)

# Save updated file
with open("seeds/sample-data/11-products.json", "w") as f:
    json.dump(updated, f, indent=2)

print(f"\n✅ Updated {cat_count} products with _category_slug references")
print(f"✅ Updated {brand_count} products with _brand_slug references")
