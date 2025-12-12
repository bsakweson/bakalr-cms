#!/usr/bin/env python3
"""
Assign products to appropriate categories based on their names/tags.
Maps products to the featured navigation categories.
"""

import requests

API_KEY = "bk_p4mPH5PGxFb9yk3jd9O12ChtBcCt8fGfDlagg70tobI"
BASE_URL = "http://localhost:8000/api/v1"

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# Keywords to map products to categories
CATEGORY_KEYWORDS = {
    "hair-care": [
        "bundle",
        "hair",
        "weave",
        "brazilian",
        "peruvian",
        "indian",
        "malaysian",
        "vietnamese",
        "cambodian",
        "burmese",
        "shampoo",
        "conditioner",
        "treatment",
        "oil",
        "leave-in",
        "deep-wave",
        "body-wave",
        "straight",
        "curly",
        "kinky",
        "loose-wave",
        "water-wave",
    ],
    "hair-styling": [
        "flat-iron",
        "curling",
        "straightener",
        "dryer",
        "brush",
        "comb",
        "gel",
        "edge",
        "mousse",
        "spray",
        "freeze",
        "hold",
        "styling",
    ],
    "wigs-extensions": [
        "wig",
        "frontal",
        "closure",
        "lace",
        "extension",
        "clip-in",
        "tape-in",
        "u-part",
        "v-part",
        "headband",
        "glueless",
        "hd-lace",
        "13x4",
        "13x6",
        "360",
        "full-lace",
        "lace-front",
    ],
    "skincare": [
        "skin",
        "face",
        "moisturizer",
        "serum",
        "cleanser",
        "toner",
        "cream",
        "lotion",
        "mask",
        "exfoliate",
        "sunscreen",
        "anti-aging",
    ],
    "cosmetics": [
        "makeup",
        "lipstick",
        "foundation",
        "eyeshadow",
        "mascara",
        "blush",
        "bronzer",
        "concealer",
        "primer",
        "lash",
        "eyeliner",
        "brow",
        "gloss",
        "tint",
        "melting",
    ],
}


def get_all_categories():
    """Fetch all categories from CMS."""
    all_cats = {}
    for page in range(1, 10):
        resp = requests.get(
            f"{BASE_URL}/content/entries",
            headers=HEADERS,
            params={"content_type_slug": "category", "page": page},
        )
        data = resp.json()
        for c in data["items"]:
            all_cats[c["slug"]] = c["id"]
        if page >= data.get("pages", 1):
            break
    return all_cats


def get_all_products():
    """Fetch all products from CMS."""
    products = []
    for page in range(1, 10):
        resp = requests.get(
            f"{BASE_URL}/content/entries",
            headers=HEADERS,
            params={"content_type_slug": "product", "page": page},
        )
        data = resp.json()
        products.extend(data["items"])
        if page >= data.get("pages", 1):
            break
    return products


def determine_category(product):
    """Determine the best category for a product based on its name and tags."""
    name = product["slug"].lower()
    title = (product.get("title") or "").lower()
    tags = [t.lower() for t in product["data"].get("tags", [])]

    searchable = f"{name} {title} {' '.join(tags)}"

    # Check each category
    scores = {}
    for cat_slug, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw in searchable:
                score += 1
        scores[cat_slug] = score

    # Return category with highest score, default to hair-care
    best_cat = max(scores, key=scores.get)
    if scores[best_cat] == 0:
        # Default based on common patterns
        if "wig" in searchable or "frontal" in searchable or "closure" in searchable:
            return "wigs-extensions"
        if "spray" in searchable or "glue" in searchable or "gel" in searchable:
            return "hair-styling"
        return "hair-care"

    return best_cat


def update_product_category(product_id, category_id):
    """Update a product's category_id."""
    resp = requests.get(f"{BASE_URL}/content/entries/{product_id}", headers=HEADERS)
    current = resp.json()

    new_data = {**current["data"], "category_id": category_id}

    resp = requests.patch(
        f"{BASE_URL}/content/entries/{product_id}", headers=HEADERS, json={"data": new_data}
    )
    return resp.status_code == 200


def main():
    print("🏷️  Assigning products to categories...\n")

    # Get all categories
    categories = get_all_categories()
    print(f"Found {len(categories)} categories")

    # Verify featured categories exist
    featured = ["hair-care", "hair-styling", "wigs-extensions", "skincare", "cosmetics"]
    for slug in featured:
        if slug in categories:
            print(f"  ✅ {slug}: {categories[slug][:8]}...")
        else:
            print(f"  ❌ {slug}: NOT FOUND")
    print()

    # Get all products
    products = get_all_products()
    print(f"Found {len(products)} products\n")

    # Assign categories
    assignments = {}
    for product in products:
        cat_slug = determine_category(product)
        if cat_slug not in assignments:
            assignments[cat_slug] = []
        assignments[cat_slug].append(product)

    # Show distribution
    print("Category distribution:")
    for cat_slug, prods in sorted(assignments.items()):
        print(f"  {cat_slug}: {len(prods)} products")
    print()

    # Update products
    updated = 0
    for cat_slug, prods in assignments.items():
        cat_id = categories.get(cat_slug)
        if not cat_id:
            print(f"  ⚠️  Skipping {cat_slug} - category not found")
            continue

        for p in prods:
            if update_product_category(p["id"], cat_id):
                updated += 1
                print(f'  ✅ {p["slug"]} -> {cat_slug}')
            else:
                print(f'  ❌ {p["slug"]} - failed')

    print(f"\n✨ Done! Updated {updated} products")


if __name__ == "__main__":
    main()
