#!/usr/bin/env python3
"""Download and upload product images to Bakalr CMS."""

import asyncio
import io

import httpx
from PIL import Image, ImageDraw, ImageFont

API_BASE = "http://localhost:8000/api/v1"
EMAIL = "bsakweson@gmail.com"
PASSWORD = "Angelbenise123!@#"

# Unsplash Source API - Free to use, no API key needed
# Format: https://source.unsplash.com/{width}x{height}/?{keywords}
UNSPLASH_BASE = "https://source.unsplash.com/1200x1200"

# Image keywords for different categories
CATEGORY_KEYWORDS = {
    "Electronics": ["technology", "gadget", "electronics", "device", "tech"],
    "Fashion": ["fashion", "clothing", "style", "apparel", "wardrobe"],
    "Home Decor": ["interior", "home", "decoration", "furniture", "modern"],
    "Beauty": ["beauty", "cosmetics", "skincare", "makeup", "wellness"],
    "Books": ["books", "reading", "library", "literature", "novel"],
    "Sports": ["fitness", "sports", "exercise", "athletic", "workout"],
    "Clothing": ["clothing", "fashion", "textile", "apparel", "wear"],
}

# Product-specific keywords for better matching
PRODUCT_KEYWORDS = {
    # Electronics
    "TV": "television,screen,display",
    "Keyboard": "keyboard,typing,computer",
    "Earbuds": "earbuds,headphones,audio",
    "Power Bank": "battery,charger,portable",
    "Mouse": "mouse,computer,gaming",
    "Docking Station": "desk,workspace,tech",
    "Webcam": "camera,video,streaming",
    "SSD": "storage,drive,technology",
    "Headphones": "headphones,audio,music",
    "Watch": "watch,smartwatch,wearable",
    # Fashion
    "Jacket": "jacket,leather,fashion",
    "Sweater": "sweater,knitwear,clothing",
    "Jeans": "jeans,denim,pants",
    "Shoes": "shoes,footwear,sneakers",
    "Coat": "coat,outerwear,winter",
    "Boots": "boots,footwear,leather",
    "Bag": "bag,handbag,accessory",
    "T-Shirt": "tshirt,clothing,casual",
    "Backpack": "backpack,bag,travel",
    "Sunglasses": "sunglasses,eyewear,fashion",
    # Home Decor
    "Lamp": "lamp,lighting,interior",
    "Clock": "clock,time,wall",
    "Art": "art,painting,canvas",
    "Vase": "vase,flowers,decoration",
    "Pillow": "pillow,cushion,comfort",
    "Rug": "rug,carpet,floor",
    "Bookshelf": "bookshelf,furniture,storage",
    "Mirror": "mirror,reflection,decor",
    "Candle": "candle,scented,home",
    # Beauty
    "Serum": "serum,skincare,beauty",
    "Lotion": "lotion,moisturizer,skincare",
    "Mask": "facemask,skincare,spa",
    "Oil": "oil,hair,beauty",
    "Brush": "makeup,brushes,cosmetics",
    # Books
    "Book": "book,reading,literature",
    "Cookbook": "cookbook,food,recipes",
    "Guide": "book,guide,learning",
    # Sports
    "Yoga Mat": "yoga,mat,fitness",
    "Fitness": "fitness,gym,exercise",
}


def create_placeholder_image(
    text: str, size=(1200, 1200), bg_color=(61, 40, 23), text_color=(255, 255, 255)
):
    """Create a placeholder image with text."""
    img = Image.new("RGB", size, color=bg_color)
    draw = ImageDraw.Draw(img)

    # Try to use a nice font, fallback to default
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 80)
    except:
        font = ImageFont.load_default()

    # Calculate text position (centered)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    position = ((size[0] - text_width) // 2, (size[1] - text_height) // 2)

    draw.text(position, text, fill=text_color, font=font)
    return img


async def download_image(url: str, timeout: int = 10) -> bytes:
    """Download image from URL."""
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url)
        if response.status_code == 200:
            return response.content
        raise Exception(f"Failed to download: {response.status_code}")


def get_search_keywords(product_name: str, category: str) -> str:
    """Get relevant search keywords for a product."""
    # Check if product name contains any known keywords
    for key, keywords in PRODUCT_KEYWORDS.items():
        if key.lower() in product_name.lower():
            return keywords

    # Fallback to category keywords
    category_keys = CATEGORY_KEYWORDS.get(category, ["product"])
    return ",".join(category_keys)


async def upload_image_to_cms(
    image_data: bytes, filename: str, product_name: str, headers: dict
) -> dict:
    """Upload image to Bakalr CMS."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        files = {"file": (filename, image_data, "image/jpeg")}
        data = {"alt_text": product_name}

        response = await client.post(
            f"{API_BASE}/media/upload",
            files=files,
            data=data,
            headers=headers,
        )

        if response.status_code in [200, 201]:
            return response.json()
        else:
            raise Exception(f"Upload failed: {response.status_code} - {response.text[:200]}")


async def link_image_to_product(product_id: int, image_url: str, headers: dict, db):
    """Update product with image URL."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get current product data
        response = await client.get(f"{API_BASE}/content/entries/{product_id}", headers=headers)
        product = response.json()

        # Update with image
        product_data = product.get("data", {})
        if "images" not in product_data:
            product_data["images"] = []

        if isinstance(product_data["images"], list):
            product_data["images"].append(image_url)
        else:
            product_data["images"] = [image_url]

        # Update product
        update_response = await client.put(
            f"{API_BASE}/content/entries/{product_id}", json={"data": product_data}, headers=headers
        )

        return update_response.status_code in [200, 201]


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
        print("📦 Fetching products...")
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

        print(f"✅ Found {len(all_products)} products\n")

        # Process each product
        print("🖼️  Adding images to products...\n")
        success = 0
        failed = 0

        for idx, product in enumerate(all_products, 1):
            product_data = product.get("data", {})
            product_name = product_data.get("name", "Unknown")
            category = product_data.get("category", "Product")
            product_id = product.get("id")

            # Skip if already has images
            existing_images = product_data.get("images", [])
            if existing_images and len(existing_images) > 0:
                print(
                    f"⏭️  [{idx}/{len(all_products)}] {product_name} - Already has images, skipping"
                )
                success += 1
                continue

            try:
                print(f"📥 [{idx}/{len(all_products)}] Processing: {product_name}")

                # Try to download from Unsplash first
                keywords = get_search_keywords(product_name, category)
                unsplash_url = f"{UNSPLASH_BASE}/?{keywords}"

                image_data = None
                filename = f"{product_id}_{product_name.replace(' ', '_')[:30]}.jpg"

                try:
                    print(f"   🌐 Downloading from Unsplash (keywords: {keywords})...")
                    image_data = await download_image(unsplash_url, timeout=10)
                    print(f"   ✅ Downloaded {len(image_data)} bytes")
                except Exception as e:
                    print(f"   ⚠️  Unsplash download failed: {str(e)}")
                    print("   🎨 Creating placeholder image...")

                    # Create placeholder image
                    img = create_placeholder_image(product_name[:20])
                    img_bytes = io.BytesIO()
                    img.save(img_bytes, format="JPEG", quality=85)
                    image_data = img_bytes.getvalue()
                    print(f"   ✅ Created placeholder ({len(image_data)} bytes)")

                # Upload to CMS
                print("   📤 Uploading to CMS...")
                upload_result = await upload_image_to_cms(
                    image_data, filename, product_name, headers
                )
                image_url = upload_result.get("public_url") or upload_result.get("url")
                print(f"   ✅ Uploaded: {image_url}")

                # Link to product
                print("   🔗 Linking to product...")
                linked = await link_image_to_product(product_id, image_url, headers, client)
                if linked:
                    print(f"   ✅ Linked to product #{product_id}")
                    success += 1
                else:
                    print("   ⚠️  Failed to link to product")
                    failed += 1

                print()

                # Small delay to avoid rate limiting
                await asyncio.sleep(0.5)

            except Exception as e:
                print(f"   ❌ Error: {str(e)}\n")
                failed += 1

        # Summary
        print("=" * 70)
        print("📊 Summary:")
        print(f"   ✅ Success: {success}/{len(all_products)} products")
        if failed > 0:
            print(f"   ❌ Failed: {failed} products")
        print("=" * 70)
        print("\n✨ Done! Check your products at: http://localhost:3000/dashboard/content")


if __name__ == "__main__":
    asyncio.run(main())
