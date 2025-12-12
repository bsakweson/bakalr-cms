#!/usr/bin/env python3
"""
Add parent categories to CMS for navigation dropdowns.
These are top-level categories that group related sub-categories.
"""

import requests

API_KEY = "bk_p4mPH5PGxFb9yk3jd9O12ChtBcCt8fGfDlagg70tobI"
BASE_URL = "http://localhost:8000/api/v1"

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# Parent categories to create
PARENT_CATEGORIES = [
    {
        "title": "Hair Care",
        "slug": "hair-care",
        "data": {
            "name": "Hair Care",
            "description": "Premium hair care products including bundles, wigs, and extensions",
            "short_description": "Premium hair care products",
            "display_order": 1,
            "featured": True,
        },
    },
    {
        "title": "Hair Styling",
        "slug": "hair-styling",
        "data": {
            "name": "Hair Styling",
            "description": "Professional hair styling tools and products",
            "short_description": "Styling tools and products",
            "display_order": 2,
            "featured": True,
        },
    },
    {
        "title": "Wigs & Extensions",
        "slug": "wigs-extensions",
        "data": {
            "name": "Wigs & Extensions",
            "description": "Premium quality wigs and hair extensions",
            "short_description": "Wigs and extensions",
            "display_order": 3,
            "featured": True,
        },
    },
    {
        "title": "Skincare",
        "slug": "skincare",
        "data": {
            "name": "Skincare",
            "description": "Luxurious skincare products for radiant skin",
            "short_description": "Skincare products",
            "display_order": 4,
            "featured": True,
        },
    },
    {
        "title": "Cosmetics",
        "slug": "cosmetics",
        "data": {
            "name": "Cosmetics",
            "description": "Professional cosmetics and makeup products",
            "short_description": "Makeup and cosmetics",
            "display_order": 5,
            "featured": True,
        },
    },
]


def get_content_type_id():
    """Get the category content type ID."""
    resp = requests.get(f"{BASE_URL}/content/types", headers=HEADERS)
    resp.raise_for_status()
    for ct in resp.json():
        if ct.get("api_id") == "category":
            return ct["id"]
    raise ValueError("Category content type not found")


def category_exists(slug: str) -> bool:
    """Check if a category with this slug exists."""
    resp = requests.get(
        f"{BASE_URL}/content/entries",
        headers=HEADERS,
        params={"content_type_slug": "category", "per_page": 100},
    )
    resp.raise_for_status()
    return any(c["slug"] == slug for c in resp.json()["items"])


def create_category(content_type_id: str, category: dict) -> bool:
    """Create a category entry."""
    if category_exists(category["slug"]):
        print(f"  ⏭️  {category['slug']} already exists, skipping")
        return False

    payload = {
        "content_type_id": content_type_id,
        "title": category["title"],
        "slug": category["slug"],
        "data": category["data"],
        "status": "published",
    }

    resp = requests.post(f"{BASE_URL}/content/entries", headers=HEADERS, json=payload)

    if resp.status_code in (200, 201):
        print(f"  ✅ Created {category['slug']}")
        return True
    else:
        print(f"  ❌ Failed to create {category['slug']}: {resp.text}")
        return False


def main():
    print("🏷️  Adding parent categories to CMS...\n")

    content_type_id = get_content_type_id()
    print(f"Category content type ID: {content_type_id}\n")

    created = 0
    skipped = 0

    for cat in PARENT_CATEGORIES:
        if create_category(content_type_id, cat):
            created += 1
        else:
            skipped += 1

    print(f"\n✨ Done! Created: {created}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
