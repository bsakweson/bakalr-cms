#!/usr/bin/env python3
"""Create curated collections for Bakalr Boutique."""

import asyncio

import httpx

API_BASE = "http://localhost:8000/api/v1"
EMAIL = "bsakweson@gmail.com"
PASSWORD = "Angelbenise123!@#"

# Collection definitions
COLLECTIONS = [
    {
        "name": "New Arrivals",
        "slug": "new-arrivals",
        "description": "<p>Check out our latest products! Fresh styles and innovative items just added to our collection.</p>",
        "is_featured": True,
        "display_order": 1,
        "filter_criteria": {"is_new": True},
    },
    {
        "name": "Bestsellers",
        "slug": "bestsellers",
        "description": "<p>Our most popular products loved by customers. These items consistently receive top ratings and rave reviews.</p>",
        "is_featured": True,
        "display_order": 2,
        "filter_criteria": {"is_featured": True},
    },
    {
        "name": "Summer Sale",
        "slug": "summer-sale",
        "description": "<p>Amazing deals and discounts! Save big on selected items during our summer sale event.</p>",
        "is_featured": True,
        "display_order": 3,
        "filter_criteria": {"on_sale": True},
    },
    {
        "name": "Eco-Friendly",
        "slug": "eco-friendly",
        "description": "<p>Sustainable and environmentally conscious products. Shop guilt-free with our eco-friendly collection.</p>",
        "is_featured": True,
        "display_order": 4,
        "filter_criteria": {"brand": "Eco Fashion"},
    },
    {
        "name": "Premium Collection",
        "slug": "premium",
        "description": "<p>Luxury items and high-end products for discerning customers. Experience quality and craftsmanship.</p>",
        "is_featured": True,
        "display_order": 5,
        "filter_criteria": {"is_featured": True, "min_price": 200},
    },
]


async def get_products_by_criteria(client, headers, criteria):
    """Fetch products matching the criteria."""
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
        if len(items) < 100:
            break
        page += 1

    # Filter products based on criteria
    matching_products = []
    for product in all_products:
        product_data = product.get("data", {})
        matches = True

        # Check each criterion
        for key, value in criteria.items():
            if key == "min_price":
                if product_data.get("price", 0) < value:
                    matches = False
                    break
            elif key == "brand":
                if product_data.get("brand") != value:
                    matches = False
                    break
            else:
                if not product_data.get(key, False):
                    matches = False
                    break

        if matches:
            matching_products.append(product["id"])

    return matching_products


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

        print("🛍️  Creating Collections...\n")

        created = 0
        failed = 0

        for collection in COLLECTIONS:
            try:
                print(f"📦 Creating: {collection['name']}")

                # Get matching products
                print("   🔍 Finding products matching criteria...")
                product_ids = await get_products_by_criteria(
                    client, headers, collection["filter_criteria"]
                )
                print(f"   ✅ Found {len(product_ids)} matching products")

                # Prepare collection data
                collection_data = {
                    "title": collection["name"],
                    "name": collection["name"],
                    "slug": collection["slug"],
                    "description": collection["description"],
                    "is_featured": collection["is_featured"],
                    "display_order": collection["display_order"],
                    "product_ids": product_ids,
                    "product_count": len(product_ids),
                }

                # Create collection
                print("   📤 Creating collection...")
                response = await client.post(
                    f"{API_BASE}/content/entries",
                    json={
                        "content_type_id": 4,  # Collection content type
                        "slug": collection["slug"],
                        "status": "published",
                        "data": collection_data,
                    },
                    headers=headers,
                )

                if response.status_code == 201:
                    result = response.json()
                    print(f"   ✅ Created: {collection['name']} (ID: {result.get('id')})")
                    print(f"   📊 Contains {len(product_ids)} products\n")
                    created += 1
                else:
                    print(f"   ❌ Failed: {response.status_code}")
                    print(f"   Error: {response.text[:200]}\n")
                    failed += 1

            except Exception as e:
                print(f"   ❌ Error: {str(e)}\n")
                failed += 1

        # Summary
        print("=" * 70)
        print("📊 Summary:")
        print(f"   ✅ Created: {created}/{len(COLLECTIONS)} collections")
        if failed > 0:
            print(f"   ❌ Failed: {failed} collections")
        print("=" * 70)

        # Show collection details
        print("\n📚 Collections Overview:\n")
        response = await client.get(
            f"{API_BASE}/content/entries",
            params={"content_type_id": 4, "page": 1, "page_size": 10},
            headers=headers,
        )

        collections = response.json().get("items", [])
        for coll in collections:
            data = coll.get("data", {})
            name = data.get("name", "Unknown")
            count = data.get("product_count", 0)
            featured = "⭐" if data.get("is_featured") else ""
            print(f"  {featured} {name}")
            print(f"     {count} products | Slug: {data.get('slug')}")
            print()

        print("✨ Done! Check collections at: http://localhost:3000/dashboard/content")


if __name__ == "__main__":
    asyncio.run(main())
