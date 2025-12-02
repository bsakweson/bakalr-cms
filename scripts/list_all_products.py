#!/usr/bin/env python3
"""List all products in the Bakalr Boutique catalog."""

import asyncio

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

        # Get all products
        print("📦 Fetching all products...")
        response = await client.get(
            f"{API_BASE}/content/entries",
            params={"content_type_id": 3, "limit": 100},
            headers=headers,
        )

        data = response.json()
        products = data.get("items", [])

        print(f"\n📊 Total Products: {len(products)}\n")

        if products:
            print("🛍️  Product Catalog:\n")
            for i, product in enumerate(products, 1):
                product_data = product.get("data", {})
                name = product_data.get("name", "Unknown")
                price = product_data.get("price", 0)
                category = product_data.get("category", "N/A")
                brand = product_data.get("brand", "N/A")
                stock = product_data.get("stock_quantity", 0)
                status = product_data.get("stock_status", "unknown")

                # Get tags
                tags = []
                if product_data.get("is_featured"):
                    tags.append("Featured")
                if product_data.get("is_new"):
                    tags.append("New")
                if product_data.get("on_sale"):
                    tags.append("On Sale")

                tag_str = f" [{', '.join(tags)}]" if tags else ""

                print(f"{i}. {name}{tag_str}")
                print(f"   💰 ${price:.2f} | 📁 {category} | 🏷️  {brand} | 📦 {stock} {status}")
                print()
        else:
            print("❌ No products found!")


if __name__ == "__main__":
    asyncio.run(main())
