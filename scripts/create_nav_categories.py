#!/usr/bin/env python3
"""Create missing parent categories for navigation menu."""

import requests

API_KEY = "bk_p4mPH5PGxFb9yk3jd9O12ChtBcCt8fGfDlagg70tobI"
BASE_URL = "http://localhost:8000"

# Categories to create with details
categories = [
    {
        "slug": "hair-care",
        "title": "Hair Care",
        "fields": {
            "name": "Hair Care",
            "slug": "hair-care",
            "description": "Premium hair care products including treatments, oils, and styling essentials.",
            "image": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=800",
            "featured": True,
            "display_order": 1,
        },
    },
    {
        "slug": "hair-styling",
        "title": "Hair Styling",
        "fields": {
            "name": "Hair Styling",
            "slug": "hair-styling",
            "description": "Professional hair styling tools and accessories.",
            "image": "https://images.unsplash.com/photo-1527799820374-dcf8d9d4a388?w=800",
            "featured": True,
            "display_order": 2,
        },
    },
    {
        "slug": "wigs-extensions",
        "title": "Wigs & Extensions",
        "fields": {
            "name": "Wigs & Extensions",
            "slug": "wigs-extensions",
            "description": "High-quality wigs, extensions, bundles, and closures.",
            "image": "https://images.unsplash.com/photo-1595476108010-b4d1f102b1b1?w=800",
            "featured": True,
            "display_order": 3,
        },
    },
    {
        "slug": "skincare",
        "title": "Skincare",
        "fields": {
            "name": "Skincare",
            "slug": "skincare",
            "description": "Luxurious skincare products for radiant, healthy skin.",
            "image": "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=800",
            "featured": True,
            "display_order": 4,
        },
    },
    {
        "slug": "cosmetics",
        "title": "Cosmetics",
        "fields": {
            "name": "Cosmetics",
            "slug": "cosmetics",
            "description": "Premium cosmetics and makeup for every look.",
            "image": "https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=800",
            "featured": True,
            "display_order": 5,
        },
    },
    {
        "slug": "nails",
        "title": "Nails",
        "fields": {
            "name": "Nails",
            "slug": "nails",
            "description": "Professional nail care products and accessories.",
            "image": "https://images.unsplash.com/photo-1604654894610-df63bc536371?w=800",
            "featured": True,
            "display_order": 6,
        },
    },
]


def main():
    print("Creating navigation categories...")

    for cat in categories:
        response = requests.post(
            f"{BASE_URL}/api/v1/content/entries",
            headers={"X-API-Key": API_KEY},
            json={
                "content_type_slug": "category",
                "slug": cat["slug"],
                "title": cat["title"],
                "status": "published",
                "fields": cat["fields"],
            },
        )
        if response.status_code in [200, 201]:
            print(f"✅ Created: {cat['title']}")
        else:
            print(f"❌ Failed: {cat['title']} - {response.status_code}: {response.text[:200]}")

    print("\nDone! Navigation categories created.")


if __name__ == "__main__":
    main()
