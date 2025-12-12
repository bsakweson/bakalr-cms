#!/usr/bin/env python3
"""
Fix Featured Categories Script

This script ensures only the 5 parent categories are marked as featured
in the Shop dropdown. All other categories will be unfeatured.

Parent categories to keep featured:
1. Hair Care (display_order: 1)
2. Hair Styling (display_order: 2)
3. Wigs & Extensions (display_order: 3)
4. Skincare (display_order: 4)
5. Cosmetics (display_order: 5)
"""

import os

import requests

# Configuration
CMS_URL = os.getenv("CMS_URL", "http://localhost:8000")
API_KEY = os.getenv("CMS_API_KEY", "bk_p4mPH5PGxFb9yk3jd9O12ChtBcCt8fGfDlagg70tobI")

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# Only these 5 parent categories should be featured
FEATURED_CATEGORIES = {
    "hair-care": {"name": "Hair Care", "display_order": 1},
    "hair-styling": {"name": "Hair Styling", "display_order": 2},
    "wigs-extensions": {"name": "Wigs & Extensions", "display_order": 3},
    "skincare": {"name": "Skincare", "display_order": 4},
    "cosmetics": {"name": "Cosmetics", "display_order": 5},
}


def get_all_categories():
    """Fetch all categories from CMS."""
    url = f"{CMS_URL}/api/v1/content/entries"
    params = {"content_type_slug": "category", "status": "published", "page_size": 100}
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json().get("items", [])


def update_category(category_id: int, data: dict):
    """Update a category's data."""
    url = f"{CMS_URL}/api/v1/content/entries/{category_id}"
    response = requests.patch(url, headers=HEADERS, json={"data": data})
    response.raise_for_status()
    return response.json()


def main():
    print("=" * 60)
    print("Fixing Featured Categories")
    print("=" * 60)

    categories = get_all_categories()
    print(f"\nFound {len(categories)} categories in CMS\n")

    unfeatured_count = 0
    featured_count = 0

    for cat in categories:
        slug = cat.get("slug")
        cat_id = cat.get("id")
        current_data = cat.get("data", {})
        name = current_data.get("name", cat.get("title", slug))
        is_featured = current_data.get("featured", False)

        if slug in FEATURED_CATEGORIES:
            # This is a parent category - ensure it's featured
            config = FEATURED_CATEGORIES[slug]
            if not is_featured or current_data.get("display_order") != config["display_order"]:
                new_data = {
                    **current_data,
                    "featured": True,
                    "display_order": config["display_order"],
                }
                update_category(cat_id, new_data)
                print(f"✅ FEATURED: {name} (order: {config['display_order']})")
                featured_count += 1
            else:
                print(f"✓  Already featured: {name}")
        elif is_featured:
            # This category is featured but shouldn't be - unfeature it
            new_data = {**current_data, "featured": False}
            update_category(cat_id, new_data)
            print(f"❌ UNFEATURED: {name}")
            unfeatured_count += 1

    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  - Categories marked as featured: {featured_count}")
    print(f"  - Categories unfeatured: {unfeatured_count}")
    print("=" * 60)

    print("\n📋 Final Featured Categories (for Shop dropdown):")
    for slug, config in sorted(FEATURED_CATEGORIES.items(), key=lambda x: x[1]["display_order"]):
        print(f"   {config['display_order']}. {config['name']} → /category/{slug}")


if __name__ == "__main__":
    main()
