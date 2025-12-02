#!/usr/bin/env python3
"""Update product records with aggregated rating and review count data."""

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

        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.text}")
            return

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Logged in successfully\n")

        # Get all content types
        print("📋 Fetching content types...")
        types_response = await client.get(f"{API_BASE}/content/types", headers=headers)
        content_types = types_response.json()

        # Find Product and Review content type IDs
        product_type = next((ct for ct in content_types if ct.get("api_id") == "product"), None)
        review_type = next((ct for ct in content_types if ct.get("api_id") == "review"), None)

        if not product_type:
            print("❌ Product content type not found")
            return

        product_type_id = product_type["id"]
        print(f"✅ Found Product content type: {product_type_id}")

        if not review_type:
            print("⚠️  Review content type not found - skipping review aggregation")
            print("💡 Run add_reviews.py first to create reviews\n")

            # Still update products with default/sample ratings
            print("📦 Fetching all products...")
            products_response = await client.get(
                f"{API_BASE}/content/entries",
                params={"content_type_id": product_type_id, "page_size": 100},
                headers=headers,
            )
            products = products_response.json().get("items", [])
            print(f"✅ Found {len(products)} products\n")

            # Add sample ratings to products
            print("⭐ Adding sample ratings to products...")
            updated = 0
            for product in products:
                product_id = product["id"]
                data = product.get("data", {})
                name = data.get("name", "Unknown")

                # Add sample rating between 4.0 and 5.0
                import random

                rating = round(random.uniform(4.0, 5.0), 1)
                review_count = random.randint(10, 250)

                # Update product data
                data["rating"] = rating
                data["review_count"] = review_count

                try:
                    await client.put(
                        f"{API_BASE}/content/entries/{product_id}",
                        json={"slug": product["slug"], "status": product["status"], "data": data},
                        headers=headers,
                    )
                    updated += 1
                    print(f"  ✓ {name[:50]:<50} {rating:.1f} ⭐ ({review_count} reviews)")
                except Exception as e:
                    print(f"  ✗ Failed to update {name}: {str(e)}")

            print(f"\n✅ Updated {updated}/{len(products)} products with sample ratings")
            return

        review_type_id = review_type["id"]
        print(f"✅ Found Review content type: {review_type_id}\n")

        # Fetch all reviews
        print("📝 Fetching all reviews...")
        reviews_response = await client.get(
            f"{API_BASE}/content/entries",
            params={"content_type_id": review_type_id, "page_size": 1000},
            headers=headers,
        )
        reviews = reviews_response.json().get("items", [])
        print(f"✅ Found {len(reviews)} reviews\n")

        # If no reviews exist, add sample ratings
        if len(reviews) == 0:
            print("⚠️  No reviews found - adding sample ratings to products\n")

            # Fetch all products
            print("📦 Fetching all products...")
            products_response = await client.get(
                f"{API_BASE}/content/entries",
                params={"content_type_id": product_type_id, "page_size": 100},
                headers=headers,
            )
            products = products_response.json().get("items", [])
            print(f"✅ Found {len(products)} products\n")

            # Add sample ratings
            print("⭐ Adding sample ratings to products...")
            import random

            updated = 0

            for product in products:
                product_id = product["id"]
                data = product.get("data", {})
                name = data.get("name", "Unknown")

                # Add sample rating between 4.0 and 5.0
                rating = round(random.uniform(4.0, 5.0), 1)
                review_count = random.randint(10, 250)

                # Update product data
                data["rating"] = rating
                data["review_count"] = review_count

                try:
                    await client.put(
                        f"{API_BASE}/content/entries/{product_id}",
                        json={"slug": product["slug"], "status": product["status"], "data": data},
                        headers=headers,
                    )
                    updated += 1
                    stars = "⭐" * int(rating)
                    print(f"  ✓ {name[:50]:<50} {rating:.1f} {stars} ({review_count} reviews)")
                except Exception as e:
                    print(f"  ✗ Failed to update {name}: {str(e)}")

            print(f"\n✅ Updated {updated}/{len(products)} products with sample ratings")
            return

        # Aggregate reviews by product
        print("🔢 Aggregating reviews by product...")
        product_reviews = defaultdict(lambda: {"ratings": [], "count": 0})

        for review in reviews:
            data = review.get("data", {})
            product_name = data.get("product_name", "")
            rating = data.get("rating", 0)

            if product_name and rating > 0:
                product_reviews[product_name]["ratings"].append(rating)
                product_reviews[product_name]["count"] += 1

        print(f"✅ Aggregated reviews for {len(product_reviews)} products\n")

        # Fetch all products and update with aggregated data
        print("📦 Fetching all products...")
        products_response = await client.get(
            f"{API_BASE}/content/entries",
            params={"content_type_id": product_type_id, "page_size": 100},
            headers=headers,
        )
        products = products_response.json().get("items", [])
        print(f"✅ Found {len(products)} products\n")

        # Update each product
        print("⭐ Updating products with review data...")
        updated = 0
        skipped = 0

        for product in products:
            product_id = product["id"]
            data = product.get("data", {})
            name = data.get("name", "Unknown")

            if name in product_reviews:
                # Calculate average rating
                ratings = product_reviews[name]["ratings"]
                avg_rating = sum(ratings) / len(ratings)
                review_count = len(ratings)

                # Update product data
                data["rating"] = round(avg_rating, 1)
                data["review_count"] = review_count

                try:
                    await client.put(
                        f"{API_BASE}/content/entries/{product_id}",
                        json={"slug": product["slug"], "status": product["status"], "data": data},
                        headers=headers,
                    )
                    updated += 1
                    stars = "⭐" * int(avg_rating)
                    print(f"  ✓ {name[:50]:<50} {avg_rating:.1f} {stars} ({review_count} reviews)")
                except Exception as e:
                    print(f"  ✗ Failed to update {name}: {str(e)}")
            else:
                skipped += 1
                print(f"  ⊘ {name[:50]:<50} No reviews")

        print(f"\n{'='*70}")
        print("📊 Summary:")
        print(f"   ✅ Updated: {updated} products")
        print(f"   ⊘ Skipped: {skipped} products (no reviews)")
        print(f"   📝 Total reviews: {len(reviews)}")
        print(f"{'='*70}")
        print("\n✨ Done! Products now display ratings on cards.")


if __name__ == "__main__":
    asyncio.run(main())
