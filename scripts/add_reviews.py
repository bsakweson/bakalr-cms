#!/usr/bin/env python3
"""Add realistic product reviews for featured products."""

import asyncio
import random
from datetime import datetime, timedelta

import httpx

API_BASE = "http://localhost:8000/api/v1"
EMAIL = "bsakweson@gmail.com"
PASSWORD = "Angelbenise123!@#"

# Review templates by rating
REVIEW_TEMPLATES = {
    5: [
        "Absolutely love this product! Exceeded my expectations in every way. {specific}",
        "Best purchase I've made this year! {specific} Highly recommend!",
        "Outstanding quality and exactly as described. {specific} Will buy again!",
        "Five stars without hesitation! {specific} Couldn't be happier!",
        "Perfect! {specific} Great value for money.",
    ],
    4: [
        "Really good product overall. {specific} Minor improvement could be made but very satisfied.",
        "Very pleased with this purchase. {specific} Would recommend.",
        "Great quality! {specific} Meets expectations.",
        "Solid choice. {specific} Happy with my purchase.",
        "Good product. {specific} Worth the price.",
    ],
}

# Specific comments by category
CATEGORY_SPECIFICS = {
    "Electronics": [
        "Works flawlessly and setup was easy.",
        "Battery life is impressive.",
        "Great build quality and feels premium.",
        "Connects seamlessly to all my devices.",
        "Performance is excellent for the price.",
    ],
    "Fashion": [
        "The fit is perfect and material feels great.",
        "Looks even better in person than in photos.",
        "Very comfortable and stylish.",
        "The quality of the fabric is excellent.",
        "Versatile and goes with everything.",
    ],
    "Home Decor": [
        "Looks beautiful in my living room.",
        "Quality craftsmanship and attention to detail.",
        "Adds a perfect touch to my space.",
        "Exactly what I was looking for.",
        "Complements my interior perfectly.",
    ],
    "Beauty": [
        "Noticed results after just a week.",
        "Skin feels amazing and looks healthier.",
        "Love the natural ingredients.",
        "No irritation and works wonderfully.",
        "Best skincare product I've tried.",
    ],
    "Books": [
        "Beautifully illustrated and informative.",
        "Well-written and easy to follow.",
        "Great addition to my collection.",
        "Learned so much from this book.",
        "High-quality printing and binding.",
    ],
    "Sports": [
        "Great for my workout routine.",
        "Durable and well-made.",
        "Perfect for beginners and pros alike.",
        "Makes exercising more enjoyable.",
        "Excellent quality for the price.",
    ],
}

# Reviewer names
REVIEWER_NAMES = [
    "Sarah M.",
    "James K.",
    "Emma L.",
    "Michael R.",
    "Olivia P.",
    "David W.",
    "Sophia T.",
    "Daniel H.",
    "Isabella C.",
    "Matthew S.",
    "Ava B.",
    "Christopher D.",
    "Mia F.",
    "Joshua G.",
    "Charlotte N.",
]


def generate_review(product_name, category, rating):
    """Generate a realistic review."""
    template = random.choice(REVIEW_TEMPLATES[rating])
    specifics = CATEGORY_SPECIFICS.get(category, ["Great product overall."])
    specific = random.choice(specifics)

    review_text = template.format(specific=specific)
    reviewer = random.choice(REVIEWER_NAMES)

    # Random date in the last 60 days
    days_ago = random.randint(1, 60)
    review_date = (datetime.now() - timedelta(days=days_ago)).isoformat()

    return {
        "reviewer_name": reviewer,
        "rating": rating,
        "review_text": review_text,
        "verified_purchase": True,
        "helpful_count": random.randint(0, 25),
        "created_at": review_date,
    }


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

        # Get featured products
        print("📦 Fetching featured products...")
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

        # Filter for featured products
        featured_products = [p for p in all_products if p.get("data", {}).get("is_featured", False)]

        print(f"✅ Found {len(featured_products)} featured products\n")

        print("⭐ Adding reviews to featured products...\n")

        total_reviews = 0
        created = 0
        failed = 0

        for product in featured_products:
            product_data = product.get("data", {})
            product_name = product_data.get("name", "Unknown")
            product_id = product.get("id")
            category = product_data.get("category", "Product")

            # Add 3-5 reviews per featured product
            num_reviews = random.randint(3, 5)

            print(f"📝 {product_name} - Adding {num_reviews} reviews")

            for i in range(num_reviews):
                try:
                    # 80% 5-star, 20% 4-star for featured products
                    rating = 5 if random.random() < 0.8 else 4

                    review_data = generate_review(product_name, category, rating)
                    review_data["product_id"] = product_id
                    review_data["product_name"] = product_name
                    review_data["title"] = f"Review for {product_name}"

                    # Create review
                    response = await client.post(
                        f"{API_BASE}/content/entries",
                        json={
                            "content_type_id": 5,  # Review content type
                            "slug": f"review-{product_id}-{i+1}",
                            "status": "published",
                            "data": review_data,
                        },
                        headers=headers,
                    )

                    if response.status_code == 201:
                        created += 1
                        total_reviews += 1
                    else:
                        failed += 1

                except Exception as e:
                    print(f"   ❌ Error adding review: {str(e)}")
                    failed += 1

            print(f"   ✅ Added {num_reviews} reviews\n")

            # Small delay
            await asyncio.sleep(0.2)

        # Summary
        print("=" * 70)
        print("📊 Summary:")
        print(f"   ✅ Added {total_reviews} reviews across {len(featured_products)} products")
        print(f"   📈 Average: {total_reviews / len(featured_products):.1f} reviews per product")
        if failed > 0:
            print(f"   ❌ Failed: {failed} reviews")
        print("=" * 70)

        # Get review count
        print("\n📊 Reviews by Product:\n")
        response = await client.get(
            f"{API_BASE}/content/entries",
            params={"content_type_id": 5, "page": 1, "page_size": 100},
            headers=headers,
        )

        reviews = response.json().get("items", [])
        review_counts = {}
        total_rating = 0

        for review in reviews:
            data = review.get("data", {})
            prod_name = data.get("product_name", "Unknown")
            rating = data.get("rating", 5)

            if prod_name not in review_counts:
                review_counts[prod_name] = {"count": 0, "total_rating": 0}

            review_counts[prod_name]["count"] += 1
            review_counts[prod_name]["total_rating"] += rating
            total_rating += rating

        for prod_name, stats in list(review_counts.items())[:10]:
            count = stats["count"]
            avg = stats["total_rating"] / count
            stars = "⭐" * int(avg)
            print(f"  {prod_name[:40]:<40} {count} reviews | {avg:.1f} {stars}")

        if len(review_counts) > 10:
            print(f"\n  ... and {len(review_counts) - 10} more products with reviews")

        overall_avg = total_rating / len(reviews) if reviews else 0
        print(f"\n  Overall Average Rating: {overall_avg:.1f} ⭐")

        print("\n✨ Done! Check reviews at: http://localhost:3000/dashboard/content")


if __name__ == "__main__":
    asyncio.run(main())
