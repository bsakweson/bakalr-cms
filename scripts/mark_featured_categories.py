#!/usr/bin/env python3
"""
Mark navigation categories as featured in CMS.
These are the top-level categories shown in the Shop dropdown.
"""

import requests

API_KEY = "bk_p4mPH5PGxFb9yk3jd9O12ChtBcCt8fGfDlagg70tobI"
BASE_URL = "http://localhost:8000/api/v1"

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# Categories to mark as featured (in display order)
FEATURED_CATEGORIES = [
    ("hair-care", 1),
    ("hair-styling", 2),
    ("wigs-extensions", 3),
    ("skincare", 4),
    ("cosmetics", 5),
]


def get_all_categories():
    """Fetch all categories from CMS."""
    all_cats = []
    page = 1
    while True:
        resp = requests.get(
            f"{BASE_URL}/content/entries",
            headers=HEADERS,
            params={"content_type_slug": "category", "page": page, "per_page": 50},
        )
        resp.raise_for_status()
        data = resp.json()
        all_cats.extend(data["items"])
        if page >= data.get("pages", 1):
            break
        page += 1
    return all_cats


def update_category(cat_id: str, cat_slug: str, display_order: int) -> bool:
    """Update a category to be featured."""
    # First get current data
    resp = requests.get(f"{BASE_URL}/content/entries/{cat_id}", headers=HEADERS)
    resp.raise_for_status()
    current = resp.json()

    # Update with featured flag and display_order
    new_data = {**current["data"], "featured": True, "display_order": display_order}

    payload = {
        "data": new_data,
    }

    resp = requests.patch(f"{BASE_URL}/content/entries/{cat_id}", headers=HEADERS, json=payload)

    if resp.status_code == 200:
        print(f"  ✅ {cat_slug} - marked as featured (order: {display_order})")
        return True
    else:
        print(f"  ❌ {cat_slug} - failed: {resp.text}")
        return False


def main():
    print("🏷️  Marking navigation categories as featured...\n")

    # Get all categories
    categories = get_all_categories()
    cat_map = {c["slug"]: c["id"] for c in categories}

    print(f"Found {len(categories)} total categories\n")

    updated = 0
    for slug, order in FEATURED_CATEGORIES:
        if slug in cat_map:
            if update_category(cat_map[slug], slug, order):
                updated += 1
        else:
            print(f"  ⚠️  {slug} - not found in CMS")

    print(f"\n✨ Done! Updated {updated} categories as featured")


if __name__ == "__main__":
    main()
