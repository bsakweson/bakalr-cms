#!/usr/bin/env python3
"""
Add color variants to hair bundle, closure, and frontal products.
"""
import json
from pathlib import Path

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

# Hair bundle products that need colors
BUNDLE_SLUGS = [
    "brazilian-body-wave-bundle",
    "vietnamese-raw-straight-bundle",
    "peruvian-loose-wave-bundle",
    "malaysian-deep-wave-bundle",
    "indian-natural-wave-bundle",
    "cambodian-raw-wavy-bundle",
    "brazilian-kinky-curly-bundle",
    "brazilian-water-wave-bundle",
]

# Closure/frontal products
CLOSURE_FRONTAL_SLUGS = [
    "hd-lace-closure-4x4-body-wave",
    "hd-lace-closure-5x5-straight",
    "hd-lace-frontal-13x4-body-wave",
    "hd-lace-frontal-13x6-deep-wave",
]


def main():
    # Path to products file
    products_file = Path(__file__).parent.parent / "seeds" / "sample-data" / "08-products.json"

    print(f"Reading: {products_file}")

    with open(products_file, "r") as f:
        data = json.load(f)

    # Products are under "entries" key
    entries = data.get("entries", data) if isinstance(data, dict) else data

    updated_count = 0

    for product in entries:
        slug = product.get("slug", "")

        if slug in BUNDLE_SLUGS:
            # Use blonde colors for Brazilian Body Wave (most popular for coloring)
            if slug == "brazilian-body-wave-bundle":
                product["data"]["available_colors"] = BLONDE_BUNDLE_COLORS
            else:
                product["data"]["available_colors"] = BUNDLE_COLORS
            print(f"✓ Added colors to: {slug}")
            updated_count += 1

        elif slug in CLOSURE_FRONTAL_SLUGS:
            product["data"]["available_colors"] = CLOSURE_COLORS
            print(f"✓ Added colors to: {slug}")
            updated_count += 1

    # Write output
    with open(products_file, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\n✅ Done! Updated {updated_count} products.")


if __name__ == "__main__":
    main()
