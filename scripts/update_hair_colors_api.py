#!/usr/bin/env python3
"""
Update existing hair products with color variants via CMS API.
"""
import os

import requests

# API configuration
API_URL = os.getenv("SEED_API_URL", "http://localhost:8000/api/v1")
API_KEY = "bk_p4mPH5PGxFb9yk3jd9O12ChtBcCt8fGfDlagg70tobI"

# Standard hair colors for bundles
BUNDLE_COLORS = [
    {"value": "natural-black", "label": "Natural Black", "hex": "#1a1a1a"},
    {"value": "1b", "label": "#1B Off Black", "hex": "#2d2d2d"},
    {"value": "2", "label": "#2 Dark Brown", "hex": "#3d2314"},
    {"value": "4", "label": "#4 Medium Brown", "hex": "#5a3825"},
]

# Colors for closures/frontals
CLOSURE_COLORS = [
    {"value": "natural-black", "label": "Natural Black", "hex": "#1a1a1a"},
    {"value": "1b", "label": "#1B Off Black", "hex": "#2d2d2d"},
    {"value": "2", "label": "#2 Dark Brown", "hex": "#3d2314"},
    {"value": "4", "label": "#4 Medium Brown", "hex": "#5a3825"},
]

# Blonde bundle colors (for products that can be lightened/colored)
BLONDE_BUNDLE_COLORS = [
    {"value": "natural-black", "label": "Natural Black", "hex": "#1a1a1a"},
    {"value": "1b", "label": "#1B Off Black", "hex": "#2d2d2d"},
    {"value": "2", "label": "#2 Dark Brown", "hex": "#3d2314"},
    {"value": "4", "label": "#4 Medium Brown", "hex": "#5a3825"},
    {"value": "27", "label": "#27 Honey Blonde", "hex": "#c99550"},
    {"value": "30", "label": "#30 Auburn", "hex": "#8b4513"},
    {"value": "613", "label": "#613 Platinum Blonde", "hex": "#f5e6c8"},
    {"value": "1b-27", "label": "Ombre 1B/27", "hex": "#2d2d2d"},
    {"value": "1b-30", "label": "Ombre 1B/30", "hex": "#2d2d2d"},
]

# Product slug to colors mapping
PRODUCT_COLORS = {
    # Bundles with blonde options
    "brazilian-body-wave-bundle": BLONDE_BUNDLE_COLORS,
    # Standard bundles
    "vietnamese-raw-straight-bundle": BUNDLE_COLORS,
    "peruvian-loose-wave-bundle": BUNDLE_COLORS,
    "malaysian-deep-wave-bundle": BUNDLE_COLORS,
    "indian-natural-wave-bundle": BUNDLE_COLORS,
    "cambodian-raw-wavy-bundle": BUNDLE_COLORS,
    "brazilian-kinky-curly-bundle": BUNDLE_COLORS,
    "brazilian-water-wave-bundle": BUNDLE_COLORS,
    # Closures and frontals
    "hd-lace-closure-4x4-body-wave": CLOSURE_COLORS,
    "hd-lace-closure-5x5-straight": CLOSURE_COLORS,
    "hd-lace-frontal-13x4-body-wave": CLOSURE_COLORS,
    "hd-lace-frontal-13x6-deep-wave": CLOSURE_COLORS,
}


def get_headers():
    return {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
    }


def get_products():
    """Fetch all products from API."""
    all_products = []
    page = 1
    while True:
        response = requests.get(
            f"{API_URL}/content/entries",
            headers=get_headers(),
            params={"content_type_slug": "product", "per_page": 100, "page": page},
        )
        response.raise_for_status()
        data = response.json()
        items = data.get("items", [])
        if not items:
            break
        all_products.extend(items)
        if page >= data.get("pages", 1):
            break
        page += 1
    return all_products


def update_product(product_id: int, data: dict):
    """Update a product via API."""
    response = requests.patch(
        f"{API_URL}/content/entries/{product_id}", headers=get_headers(), json={"data": data}
    )
    response.raise_for_status()
    return response.json()


def main():
    print(f"API URL: {API_URL}")
    print("Fetching products...")

    products = get_products()
    print(f"Found {len(products)} products\n")

    updated_count = 0

    for product in products:
        slug = product.get("slug", "")
        product_id = product.get("id")

        if slug in PRODUCT_COLORS:
            colors = PRODUCT_COLORS[slug]

            # Get current product data
            current_data = product.get("data", {})
            current_data["available_colors"] = colors

            try:
                update_product(product_id, current_data)
                print(f"✓ Updated: {slug} (ID: {product_id}) - {len(colors)} colors")
                updated_count += 1
            except requests.HTTPError as e:
                print(f"✗ Failed to update {slug}: {e}")

    print(f"\n✅ Done! Updated {updated_count} products with color variants.")


if __name__ == "__main__":
    main()
