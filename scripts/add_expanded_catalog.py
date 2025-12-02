#!/usr/bin/env python3
"""Add an expanded product catalog with diverse categories and realistic variety."""

import asyncio

import httpx

API_BASE = "http://localhost:8000/api/v1"
EMAIL = "bsakweson@gmail.com"
PASSWORD = "Angelbenise123!@#"

# Expanded product catalog with diverse categories
PRODUCTS = [
    # Electronics - 8 products
    {
        "name": "4K Ultra HD Smart TV",
        "sku": "TV-SMART-55",
        "description": "<p>55-inch 4K Ultra HD Smart TV with HDR, built-in streaming apps, and voice control. Perfect for home entertainment.</p>",
        "price": 649.99,
        "sale_price": 549.99,
        "category": "Electronics",
        "brand": "TechPro",
        "stock_quantity": 15,
        "stock_status": "in_stock",
        "is_featured": True,
        "on_sale": True,
        "specifications": {
            "screen_size": "55 inches",
            "resolution": "4K UHD",
            "smart_features": "Yes",
            "hdmi_ports": 4,
        },
    },
    {
        "name": "Mechanical Gaming Keyboard",
        "sku": "KB-GAMING-RGB",
        "description": "<p>RGB mechanical gaming keyboard with Cherry MX switches, customizable backlighting, and programmable keys.</p>",
        "price": 159.99,
        "category": "Electronics",
        "brand": "TechPro",
        "stock_quantity": 45,
        "stock_status": "in_stock",
        "is_new": True,
        "specifications": {"switch_type": "Cherry MX Red", "rgb": "Yes", "connectivity": "USB-C"},
    },
    {
        "name": "Noise Cancelling Earbuds Pro",
        "sku": "EARBUDS-NC-PRO",
        "description": "<p>Premium wireless earbuds with active noise cancellation, 30-hour battery life, and crystal-clear audio.</p>",
        "price": 199.99,
        "category": "Electronics",
        "brand": "TechPro",
        "stock_quantity": 80,
        "stock_status": "in_stock",
        "is_featured": True,
        "is_new": True,
        "specifications": {"battery_life": "30 hours", "anc": "Yes", "water_resistance": "IPX4"},
    },
    {
        "name": "Portable Power Bank 20000mAh",
        "sku": "PWR-BANK-20K",
        "description": "<p>High-capacity power bank with fast charging, dual USB ports, and LED display. Charges multiple devices.</p>",
        "price": 49.99,
        "category": "Electronics",
        "brand": "TechPro",
        "stock_quantity": 150,
        "stock_status": "in_stock",
        "specifications": {"capacity": "20000mAh", "fast_charging": "Yes", "ports": 2},
    },
    {
        "name": "Wireless Gaming Mouse",
        "sku": "MOUSE-GAME-WL",
        "description": "<p>High-precision wireless gaming mouse with 16000 DPI sensor, customizable buttons, and RGB lighting.</p>",
        "price": 89.99,
        "sale_price": 69.99,
        "category": "Electronics",
        "brand": "TechPro",
        "stock_quantity": 60,
        "stock_status": "in_stock",
        "on_sale": True,
        "specifications": {"dpi": 16000, "wireless": "Yes", "programmable_buttons": 8},
    },
    {
        "name": "USB-C Docking Station",
        "sku": "DOCK-USBC-PRO",
        "description": "<p>Professional USB-C docking station with dual 4K display support, ethernet, and multiple ports.</p>",
        "price": 179.99,
        "category": "Electronics",
        "brand": "TechPro",
        "stock_quantity": 35,
        "stock_status": "in_stock",
        "specifications": {"displays_supported": 2, "4k_support": "Yes", "ethernet": "Gigabit"},
    },
    {
        "name": "Webcam HD 1080p",
        "sku": "CAM-HD-1080",
        "description": "<p>Full HD 1080p webcam with auto-focus, built-in microphone, and wide-angle lens. Perfect for video calls.</p>",
        "price": 79.99,
        "category": "Electronics",
        "brand": "TechPro",
        "stock_quantity": 90,
        "stock_status": "in_stock",
        "is_new": True,
        "specifications": {
            "resolution": "1080p",
            "auto_focus": "Yes",
            "field_of_view": "90 degrees",
        },
    },
    {
        "name": "Portable SSD 1TB",
        "sku": "SSD-PORT-1TB",
        "description": "<p>Ultra-fast portable SSD with 1TB storage, USB 3.2 Gen 2 speeds up to 1050MB/s, and compact design.</p>",
        "price": 139.99,
        "category": "Electronics",
        "brand": "TechPro",
        "stock_quantity": 55,
        "stock_status": "in_stock",
        "is_featured": True,
        "specifications": {"capacity": "1TB", "speed": "1050MB/s", "interface": "USB 3.2 Gen 2"},
    },
    # Fashion - 6 products
    {
        "name": "Cashmere Blend Sweater",
        "sku": "SWTR-CASH-BLUE",
        "description": "<p>Luxurious cashmere blend sweater in midnight blue. Soft, warm, and perfect for any occasion.</p>",
        "price": 159.99,
        "category": "Fashion",
        "brand": "Bakalr Original",
        "stock_quantity": 40,
        "stock_status": "in_stock",
        "is_featured": True,
        "specifications": {"material": "80% Wool, 20% Cashmere", "care": "Dry clean only"},
    },
    {
        "name": "Slim Fit Denim Jeans",
        "sku": "JEANS-SLIM-DARK",
        "description": "<p>Classic slim-fit dark wash jeans with stretch denim for comfort. Timeless style that never goes out of fashion.</p>",
        "price": 89.99,
        "sale_price": 69.99,
        "category": "Fashion",
        "brand": "Urban Style",
        "stock_quantity": 120,
        "stock_status": "in_stock",
        "on_sale": True,
        "specifications": {"fit": "Slim", "material": "98% Cotton, 2% Elastane"},
    },
    {
        "name": "Running Shoes Performance",
        "sku": "SHOE-RUN-PERF",
        "description": "<p>High-performance running shoes with responsive cushioning, breathable mesh, and superior traction.</p>",
        "price": 129.99,
        "category": "Fashion",
        "brand": "ActiveLife",
        "stock_quantity": 85,
        "stock_status": "in_stock",
        "is_new": True,
        "specifications": {"type": "Running", "cushioning": "Responsive foam", "weight": "240g"},
    },
    {
        "name": "Wool Winter Coat",
        "sku": "COAT-WOOL-GRY",
        "description": "<p>Premium wool winter coat in charcoal grey. Tailored fit with inner lining for warmth and style.</p>",
        "price": 349.99,
        "category": "Fashion",
        "brand": "Bakalr Original",
        "stock_quantity": 25,
        "stock_status": "in_stock",
        "is_featured": True,
        "specifications": {"material": "90% Wool, 10% Polyester", "lining": "100% Silk"},
    },
    {
        "name": "Leather Ankle Boots",
        "sku": "BOOT-LEATH-BLK",
        "description": "<p>Classic black leather ankle boots with comfortable heel and versatile design. Perfect for any outfit.</p>",
        "price": 179.99,
        "category": "Fashion",
        "brand": "Urban Style",
        "stock_quantity": 60,
        "stock_status": "in_stock",
        "specifications": {
            "material": "Genuine leather",
            "heel_height": "5cm",
            "closure": "Zipper",
        },
    },
    {
        "name": "Cotton Canvas Tote Bag",
        "sku": "BAG-TOTE-NATRL",
        "description": "<p>Eco-friendly canvas tote bag in natural color. Spacious, durable, and perfect for shopping or beach days.</p>",
        "price": 34.99,
        "category": "Fashion",
        "brand": "Eco Fashion",
        "stock_quantity": 200,
        "stock_status": "in_stock",
        "is_new": True,
        "specifications": {"material": "100% Organic Cotton", "capacity": "20L"},
    },
    # Home Decor - 6 products
    {
        "name": "Abstract Canvas Art Print",
        "sku": "ART-CANVAS-ABS",
        "description": "<p>Modern abstract canvas art print in vibrant colors. Gallery-quality print on premium canvas with wooden frame.</p>",
        "price": 129.99,
        "category": "Home Decor",
        "brand": "Classic Home",
        "stock_quantity": 45,
        "stock_status": "in_stock",
        "is_featured": True,
        "specifications": {"size": "60x90cm", "frame": "Wood", "canvas": "Museum quality"},
    },
    {
        "name": "Ceramic Vase Set",
        "sku": "VASE-CERAM-SET3",
        "description": "<p>Set of 3 minimalist ceramic vases in white and grey. Perfect for fresh or dried flowers.</p>",
        "price": 59.99,
        "category": "Home Decor",
        "brand": "Classic Home",
        "stock_quantity": 80,
        "stock_status": "in_stock",
        "specifications": {"pieces": 3, "material": "Ceramic", "heights": "20cm, 25cm, 30cm"},
    },
    {
        "name": "Throw Pillow Velvet",
        "sku": "PILLOW-VEL-GREY",
        "description": "<p>Luxurious velvet throw pillow in charcoal grey. Soft texture with hidden zipper and plush filling.</p>",
        "price": 39.99,
        "sale_price": 29.99,
        "category": "Home Decor",
        "brand": "Classic Home",
        "stock_quantity": 150,
        "stock_status": "in_stock",
        "on_sale": True,
        "specifications": {"size": "45x45cm", "material": "Velvet", "filling": "Polyester"},
    },
    {
        "name": "Area Rug Modern Geometric",
        "sku": "RUG-GEO-160X230",
        "description": "<p>Modern geometric area rug in neutral tones. Soft pile, durable construction, perfect for living rooms.</p>",
        "price": 199.99,
        "category": "Home Decor",
        "brand": "Classic Home",
        "stock_quantity": 30,
        "stock_status": "in_stock",
        "is_featured": True,
        "specifications": {"size": "160x230cm", "pile_height": "15mm", "material": "Polypropylene"},
    },
    {
        "name": "Bookshelf Ladder Style",
        "sku": "SHELF-LADD-WOOD",
        "description": "<p>Modern ladder-style bookshelf in walnut finish. 5 tiers for books, plants, and decor items.</p>",
        "price": 179.99,
        "category": "Home Decor",
        "brand": "Classic Home",
        "stock_quantity": 25,
        "stock_status": "in_stock",
        "is_new": True,
        "specifications": {
            "tiers": 5,
            "material": "Wood",
            "finish": "Walnut",
            "load_capacity": "50kg",
        },
    },
    {
        "name": "Floor Mirror Full Length",
        "sku": "MIRROR-FLOOR-BLK",
        "description": "<p>Full-length floor mirror with sleek black metal frame. Leaning design, perfect for bedrooms or dressing areas.</p>",
        "price": 159.99,
        "category": "Home Decor",
        "brand": "Classic Home",
        "stock_quantity": 35,
        "stock_status": "in_stock",
        "specifications": {"size": "60x170cm", "frame": "Metal", "type": "Leaning"},
    },
    # Books - 5 products
    {
        "name": "The Art of Minimalism",
        "sku": "BOOK-MIN-ART",
        "description": "<p>A comprehensive guide to minimalist living, decluttering, and finding peace in simplicity. Hardcover edition.</p>",
        "price": 29.99,
        "category": "Books",
        "brand": "Classic Home",
        "stock_quantity": 100,
        "stock_status": "in_stock",
        "is_new": True,
        "specifications": {"format": "Hardcover", "pages": 320, "language": "English"},
    },
    {
        "name": "Modern Architecture Handbook",
        "sku": "BOOK-ARCH-MOD",
        "description": "<p>Stunning photography and insights into contemporary architecture. Coffee table book with 500+ images.</p>",
        "price": 49.99,
        "category": "Books",
        "brand": "Classic Home",
        "stock_quantity": 60,
        "stock_status": "in_stock",
        "is_featured": True,
        "specifications": {
            "format": "Hardcover",
            "pages": 480,
            "images": "500+",
            "dimensions": "30x40cm",
        },
    },
    {
        "name": "Cookbook Mediterranean Flavors",
        "sku": "BOOK-COOK-MED",
        "description": "<p>Delicious Mediterranean recipes with beautiful food photography. Over 200 recipes from the region.</p>",
        "price": 34.99,
        "category": "Books",
        "brand": "Classic Home",
        "stock_quantity": 80,
        "stock_status": "in_stock",
        "specifications": {"format": "Hardcover", "recipes": 200, "pages": 280},
    },
    {
        "name": "Photography Basics Guide",
        "sku": "BOOK-PHOTO-101",
        "description": "<p>Learn photography fundamentals from composition to lighting. Includes practical exercises and examples.</p>",
        "price": 24.99,
        "category": "Books",
        "brand": "Classic Home",
        "stock_quantity": 90,
        "stock_status": "in_stock",
        "is_new": True,
        "specifications": {"format": "Paperback", "pages": 240, "illustrations": "150+"},
    },
    {
        "name": "Houseplants Complete Guide",
        "sku": "BOOK-PLANT-CARE",
        "description": "<p>Everything you need to know about indoor plants. Care tips, troubleshooting, and profiles of 100+ plants.</p>",
        "price": 27.99,
        "category": "Books",
        "brand": "Classic Home",
        "stock_quantity": 75,
        "stock_status": "in_stock",
        "specifications": {"format": "Paperback", "pages": 200, "plant_profiles": 100},
    },
    # Beauty - 5 products
    {
        "name": "Natural Face Serum Vitamin C",
        "sku": "SERUM-FACE-VITC",
        "description": "<p>Organic vitamin C face serum with hyaluronic acid. Brightens skin, reduces dark spots, and boosts collagen.</p>",
        "price": 44.99,
        "category": "Beauty",
        "brand": "Eco Fashion",
        "stock_quantity": 120,
        "stock_status": "in_stock",
        "is_featured": True,
        "is_new": True,
        "specifications": {"volume": "30ml", "ingredients": "Organic", "vitamin_c": "20%"},
    },
    {
        "name": "Moisturizing Body Lotion",
        "sku": "LOTION-BODY-MOIST",
        "description": "<p>Rich moisturizing body lotion with shea butter and aloe vera. Non-greasy formula for soft, hydrated skin.</p>",
        "price": 24.99,
        "category": "Beauty",
        "brand": "Eco Fashion",
        "stock_quantity": 200,
        "stock_status": "in_stock",
        "specifications": {
            "volume": "250ml",
            "key_ingredients": "Shea butter, Aloe vera",
            "paraben_free": "Yes",
        },
    },
    {
        "name": "Clay Face Mask Detox",
        "sku": "MASK-FACE-CLAY",
        "description": "<p>Detoxifying clay face mask with charcoal. Deep cleanses pores, removes impurities, and mattifies skin.</p>",
        "price": 19.99,
        "category": "Beauty",
        "brand": "Eco Fashion",
        "stock_quantity": 150,
        "stock_status": "in_stock",
        "is_new": True,
        "specifications": {"volume": "100ml", "clay_type": "Bentonite", "charcoal": "Activated"},
    },
    {
        "name": "Argan Oil Hair Treatment",
        "sku": "HAIR-OIL-ARGAN",
        "description": "<p>Pure argan oil hair treatment for shine and repair. Tames frizz, nourishes ends, heat protectant.</p>",
        "price": 29.99,
        "category": "Beauty",
        "brand": "Eco Fashion",
        "stock_quantity": 100,
        "stock_status": "in_stock",
        "specifications": {"volume": "50ml", "purity": "100% Argan oil", "origin": "Morocco"},
    },
    {
        "name": "Makeup Brush Set Professional",
        "sku": "BRUSH-SET-PRO12",
        "description": "<p>Professional makeup brush set with 12 essential brushes. Soft synthetic bristles, bamboo handles, includes case.</p>",
        "price": 59.99,
        "sale_price": 44.99,
        "category": "Beauty",
        "brand": "Urban Style",
        "stock_quantity": 80,
        "stock_status": "in_stock",
        "on_sale": True,
        "is_featured": True,
        "specifications": {
            "pieces": 12,
            "bristles": "Synthetic",
            "handles": "Bamboo",
            "case": "Included",
        },
    },
]


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

        # Add products
        print(f"🛍️  Adding {len(PRODUCTS)} Products to Catalog...\n")

        created = 0
        failed = 0

        for product in PRODUCTS:
            try:
                # Prepare product data (includes title)
                product_data = product.copy()
                product_data["title"] = product["name"]

                # Create product entry
                response = await client.post(
                    f"{API_BASE}/content/entries",
                    json={
                        "content_type_id": 3,  # Product content type
                        "slug": product["sku"].lower(),
                        "status": "published",
                        "data": product_data,
                    },
                    headers=headers,
                )

                if response.status_code == 201:
                    print(f"✅ Created: {product['name']}")
                    created += 1
                else:
                    print(f"❌ Failed: {product['name']} - {response.status_code}")
                    print(f"   Error: {response.text[:200]}")
                    failed += 1

            except Exception as e:
                print(f"❌ Error adding {product['name']}: {str(e)}")
                failed += 1

        # Summary
        print(f"\n{'='*60}")
        print(f"📊 Summary: Created {created} out of {len(PRODUCTS)} products")
        if failed > 0:
            print(f"⚠️  Failed: {failed} products")

        # Get final count
        response = await client.get(
            f"{API_BASE}/content/entries",
            params={"content_type_id": 3, "limit": 1},
            headers=headers,
        )
        total = response.json().get("total", 0)
        print(f"📦 Total products in catalog: {total}")
        print(f"{'='*60}")
        print("\n✅ Done! Check your products at: http://localhost:3000/dashboard/content")


if __name__ == "__main__":
    asyncio.run(main())
