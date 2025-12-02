#!/usr/bin/env python3
"""Generate a comprehensive catalog summary by category."""

import asyncio
from collections import defaultdict

import httpx

API_BASE = "http://localhost:8000/api/v1"
EMAIL = "bsakweson@gmail.com"
PASSWORD = "Angelbenise123!@#"


async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Login
        print("🔐 Logging in...")
        login_response = await client.post(
            f"{API_BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Logged in\n")

        # Get all products (handle pagination)
        all_products = []
        page = 1
        while True:
            response = await client.get(
                f"{API_BASE}/content/entries",
                params={"content_type_id": 3, "page": page, "page_size": 100},
                headers=headers,
            )
            data = response.json()
            items = data.get("items", [])
            if not items:
                break
            all_products.extend(items)
            # Check if there are more pages
            if len(items) < 100:
                break
            page += 1

        products = all_products

        # Categorize products
        by_category = defaultdict(list)
        by_brand = defaultdict(int)
        featured = []
        on_sale = []
        new_arrivals = []

        price_min = float("inf")
        price_max = 0

        for product in products:
            data = product.get("data", {})
            category = data.get("category", "Unknown")
            brand = data.get("brand", "Unknown")
            price = data.get("price", 0)

            by_category[category].append(data.get("name", "Unknown"))
            by_brand[brand] += 1

            if data.get("is_featured"):
                featured.append(data.get("name"))
            if data.get("on_sale"):
                on_sale.append(data.get("name"))
            if data.get("is_new"):
                new_arrivals.append(data.get("name"))

            price_min = min(price_min, price)
            price_max = max(price_max, price)

        # Print summary
        print("=" * 70)
        print("📊 BAKALR BOUTIQUE CATALOG SUMMARY")
        print("=" * 70)
        print(f"\n📦 Total Products: {len(products)}")
        print(f"💰 Price Range: ${price_min:.2f} - ${price_max:.2f}\n")

        print("📁 Products by Category:")
        for category, items in sorted(by_category.items()):
            print(f"  • {category}: {len(items)} products")

        print("\n🏷️  Products by Brand:")
        for brand, count in sorted(by_brand.items(), key=lambda x: -x[1]):
            print(f"  • {brand}: {count} products")

        print(f"\n⭐ Featured Products: {len(featured)}")
        for name in featured[:5]:
            print(f"  • {name}")
        if len(featured) > 5:
            print(f"  ... and {len(featured) - 5} more")

        print(f"\n🔥 On Sale: {len(on_sale)}")
        for name in on_sale:
            print(f"  • {name}")

        print(f"\n🆕 New Arrivals: {len(new_arrivals)}")
        for name in new_arrivals[:5]:
            print(f"  • {name}")
        if len(new_arrivals) > 5:
            print(f"  ... and {len(new_arrivals) - 5} more")

        print("\n" + "=" * 70)
        print("✅ Catalog Summary Complete!")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
