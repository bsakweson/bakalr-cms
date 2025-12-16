#!/usr/bin/env python3
"""Fix product category mappings based on product names/slugs."""

import json

# Load products
with open("seeds/sample-data/11-products.json", "r") as f:
    products = json.load(f)

# Correct category mappings based on product type
category_mappings = {
    # Hair bundles -> hair-extensions or specific origin
    "vietnamese-raw-straight-bundle": "vietnamese-hair",
    "peruvian-loose-wave-bundle": "peruvian-hair",
    "malaysian-deep-wave-bundle": "malaysian-hair",
    "indian-natural-wave-bundle": "indian-hair",
    "cambodian-raw-wavy-bundle": "cambodian-hair",
    "brazilian-kinky-curly-bundle": "brazilian-hair",
    "brazilian-water-wave-bundle": "brazilian-hair",
    # Closures and frontals
    "hd-lace-closure-4x4-body-wave": "closures",
    "hd-lace-closure-5x5-straight": "closures",
    "hd-lace-frontal-13x4-body-wave": "frontals",
    "hd-lace-frontal-13x6-deep-wave": "frontals",
    # Wigs
    "glueless-lace-front-wig-body-wave": "glueless-wigs",
    "full-lace-wig-straight-613-blonde": "full-lace-wigs",
    # Wig accessories
    "ebin-wonder-lace-bond-wig-glue": "wig-glue-adhesive",
    "got2b-glued-blasting-freeze-spray": "hair-styling",
    "bold-hold-lace-tint-spray": "lace-melting",
    "wig-grip-band-velvet": "wig-accessories",
}

# Update products
for product in products:
    slug = product["slug"]

    # Remove category_id from content_data if present
    if "category_id" in product.get("content_data", {}):
        del product["content_data"]["category_id"]

    # Remove brand_id from content_data if present
    if "brand_id" in product.get("content_data", {}):
        del product["content_data"]["brand_id"]

    # Set correct _category_slug
    if slug in category_mappings:
        product["_category_slug"] = category_mappings[slug]
        print(f"✅ {slug} -> {category_mappings[slug]}")
    else:
        print(f"⚠️  {slug} - no mapping found, keeping as-is")

# Save updated products
with open("seeds/sample-data/11-products.json", "w") as f:
    json.dump(products, f, indent=2)

print(f"\n✅ Updated {len(products)} products")
