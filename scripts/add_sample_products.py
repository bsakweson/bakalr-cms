#!/usr/bin/env python3
"""
Quick script to add sample products to Bakalr Boutique
Uses existing content types and adds sample data only
"""

import asyncio

import httpx

# Configuration
API_BASE = "http://localhost:8000/api/v1"
EMAIL = "bsakweson@gmail.com"
PASSWORD = "Angelbenise123!@#"


async def main():
    client = httpx.AsyncClient(timeout=30.0)

    # Login
    print("🔐 Logging in...")
    resp = await client.post(f"{API_BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if resp.status_code != 200:
        print(f"❌ Login failed: {resp.text}")
        return

    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Logged in\n")

    # Add more products
    print("🛍️  Adding Sample Products...\n")

    products = [
        {
            "name": "Classic Leather Jacket",
            "sku": "JACKET-001",
            "description": "<p>Genuine leather jacket with classic styling. Perfect for any season.</p>",
            "price": 299.99,
            "category": "Fashion",
            "brand": "Bakalr Original",
            "stock_quantity": 50,
            "stock_status": "in_stock",
            "is_featured": True,
            "is_new": False,
            "is_on_sale": False,
            "tags": "leather, jacket, classic, outerwear",
            "currency": "USD",
        },
        {
            "name": "Modern Table Lamp",
            "sku": "LAMP-001",
            "description": "<p>Contemporary design with adjustable brightness. Energy-efficient LED bulb included.</p>",
            "price": 89.99,
            "sale_price": 69.99,
            "category": "Home Decor",
            "brand": "Classic Home",
            "stock_quantity": 100,
            "stock_status": "in_stock",
            "is_featured": True,
            "is_on_sale": True,
            "tags": "lamp, lighting, home, decor, LED",
            "currency": "USD",
        },
        {
            "name": "Organic Cotton T-Shirt",
            "sku": "TSHIRT-001",
            "description": "<p>Sustainable organic cotton, available in multiple colors. Soft and breathable.</p>",
            "price": 39.99,
            "category": "Fashion",
            "brand": "Eco Fashion",
            "stock_quantity": 200,
            "stock_status": "in_stock",
            "is_new": True,
            "tags": "organic, cotton, sustainable, tshirt",
            "currency": "USD",
        },
        {
            "name": "Minimalist Wall Clock",
            "sku": "CLOCK-001",
            "description": "<p>Elegant minimalist design for modern homes. Silent quartz movement.</p>",
            "price": 59.99,
            "category": "Home Decor",
            "brand": "Classic Home",
            "stock_quantity": 75,
            "stock_status": "in_stock",
            "tags": "clock, wall, minimalist, home",
            "currency": "USD",
        },
        {
            "name": "Urban Backpack",
            "sku": "BACKPACK-001",
            "description": "<p>Durable backpack for city life and travel. Multiple compartments for organization.</p>",
            "price": 79.99,
            "category": "Fashion",
            "brand": "Urban Style",
            "stock_quantity": 120,
            "stock_status": "in_stock",
            "tags": "backpack, travel, urban, bag",
            "currency": "USD",
        },
        {
            "name": "Designer Sunglasses",
            "sku": "SUNGLASSES-001",
            "description": "<p>Premium UV protection with stylish frames. Includes protective case.</p>",
            "price": 149.99,
            "sale_price": 119.99,
            "category": "Fashion",
            "brand": "Urban Style",
            "stock_quantity": 85,
            "stock_status": "in_stock",
            "is_featured": True,
            "is_on_sale": True,
            "tags": "sunglasses, accessories, UV protection",
            "currency": "USD",
        },
        {
            "name": "Eco-Friendly Water Bottle",
            "sku": "BOTTLE-001",
            "description": "<p>Stainless steel insulated bottle. Keeps drinks cold for 24hrs, hot for 12hrs.</p>",
            "price": 34.99,
            "category": "Fashion",
            "brand": "Eco Fashion",
            "stock_quantity": 150,
            "stock_status": "in_stock",
            "is_new": True,
            "tags": "water bottle, eco-friendly, insulated, sustainable",
            "currency": "USD",
        },
        {
            "name": "Scented Candle Set",
            "sku": "CANDLES-001",
            "description": "<p>Set of 3 luxury scented candles. Made with natural soy wax.</p>",
            "price": 45.99,
            "category": "Home Decor",
            "brand": "Classic Home",
            "stock_quantity": 90,
            "stock_status": "in_stock",
            "tags": "candles, home fragrance, decor, soy wax",
            "currency": "USD",
        },
        {
            "name": "Wireless Earbuds",
            "sku": "EARBUDS-001",
            "description": "<p>High-quality audio with active noise cancellation. 24-hour battery life.</p>",
            "price": 129.99,
            "category": "Electronics",
            "brand": "Urban Style",
            "stock_quantity": 60,
            "stock_status": "in_stock",
            "is_featured": True,
            "is_new": True,
            "tags": "earbuds, wireless, audio, electronics",
            "currency": "USD",
        },
        {
            "name": "Yoga Mat Premium",
            "sku": "YOGA-001",
            "description": "<p>Extra thick cushioning for comfort. Non-slip surface with carrying strap.</p>",
            "price": 54.99,
            "category": "Sports",
            "brand": "Eco Fashion",
            "stock_quantity": 110,
            "stock_status": "in_stock",
            "tags": "yoga, mat, fitness, exercise",
            "currency": "USD",
        },
    ]

    created_count = 0
    for product in products:
        # Add title to data
        product_data = product.copy()
        product_data["title"] = product["name"]

        resp = await client.post(
            f"{API_BASE}/content/entries",
            json={
                "content_type_id": 3,  # Product content type
                "slug": product["sku"].lower(),
                "status": "published",
                "data": product_data,
            },
            headers=headers,
        )

        if resp.status_code in [200, 201]:
            created_count += 1
            print(f"✅ Created: {product['name']}")
        else:
            print(f"⚠️  Failed to create {product['name']}: {resp.status_code}")
            if resp.status_code != 409:  # Not a duplicate error
                print(f"   Error: {resp.text[:200]}")

    print(f"\n📊 Summary: Created {created_count} out of {len(products)} products")

    # Check total products now
    resp = await client.get(f"{API_BASE}/content/entries?content_type_id=3", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        items = data.get("items", data)
        total = len(items) if isinstance(items, list) else data.get("total", 0)
        print(f"📦 Total products in catalog: {total}")

    print("\n✅ Done! Check your products at: http://localhost:3000/dashboard/content")

    await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
