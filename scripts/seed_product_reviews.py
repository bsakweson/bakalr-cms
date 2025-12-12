#!/usr/bin/env python3
"""
Seed product reviews into the CMS.
Run with: cat scripts/seed_product_reviews.py | docker exec -i bakalr-backend python3 -
"""

import os
import sys

sys.path.insert(0, "/app")
os.chdir("/app")

import json
import uuid
from datetime import datetime

from backend.db.session import SessionLocal
from backend.models.content import ContentEntry, ContentType
from backend.models.user import User

# Sample reviews data
REVIEWS = [
    {
        "slug": "review-sarah-brazilian-water-wave",
        "title": "Absolutely love it!",
        "status": "published",
        "data": {
            "product_id": "brazilian-water-wave-bundle",
            "customer_name": "Sarah M.",
            "customer_email": "sarah.m@example.com",
            "rating": 5,
            "title": "Absolutely love it!",
            "body": "This product exceeded my expectations. The quality is amazing and it looks exactly like the pictures. Highly recommend to anyone considering it.",
            "verified_purchase": True,
            "helpful_count": 12,
            "review_date": "2025-11-30",
        },
    },
    {
        "slug": "review-michelle-brazilian-water-wave",
        "title": "Great quality, fast shipping",
        "status": "published",
        "data": {
            "product_id": "brazilian-water-wave-bundle",
            "customer_name": "Michelle T.",
            "customer_email": "michelle.t@example.com",
            "rating": 4,
            "title": "Great quality, fast shipping",
            "body": "Very happy with my purchase. The product arrived quickly and was well packaged. Only giving 4 stars because the color was slightly different from what I expected.",
            "verified_purchase": True,
            "helpful_count": 8,
            "review_date": "2025-11-27",
        },
    },
    {
        "slug": "review-jessica-brazilian-water-wave",
        "title": "Best purchase ever!",
        "status": "published",
        "data": {
            "product_id": "brazilian-water-wave-bundle",
            "customer_name": "Jessica L.",
            "customer_email": "jessica.l@example.com",
            "rating": 5,
            "title": "Best purchase ever!",
            "body": "I've been looking for something like this for months. Finally found it here and it's perfect. Will definitely be ordering again.",
            "verified_purchase": False,
            "helpful_count": 5,
            "review_date": "2025-11-24",
        },
    },
    {
        "slug": "review-amanda-brazilian-water-wave",
        "title": "Good but could be better",
        "status": "published",
        "data": {
            "product_id": "brazilian-water-wave-bundle",
            "customer_name": "Amanda K.",
            "customer_email": "amanda.k@example.com",
            "rating": 3,
            "title": "Good but could be better",
            "body": "The product is decent for the price. It does what it's supposed to do but I feel like there's room for improvement in the packaging.",
            "verified_purchase": True,
            "helpful_count": 3,
            "review_date": "2025-11-20",
        },
    },
    {
        "slug": "review-tanisha-brazilian-kinky-curly",
        "title": "Perfect curls!",
        "status": "published",
        "data": {
            "product_id": "brazilian-kinky-curly-bundle",
            "customer_name": "Tanisha W.",
            "customer_email": "tanisha.w@example.com",
            "rating": 5,
            "title": "Perfect curls!",
            "body": "The curls are absolutely gorgeous and hold their pattern even after washing. Minimal shedding and tangling. This is my third purchase!",
            "verified_purchase": True,
            "helpful_count": 15,
            "review_date": "2025-12-01",
        },
    },
    {
        "slug": "review-kendra-brazilian-kinky-curly",
        "title": "Beautiful texture",
        "status": "published",
        "data": {
            "product_id": "brazilian-kinky-curly-bundle",
            "customer_name": "Kendra J.",
            "customer_email": "kendra.j@example.com",
            "rating": 4,
            "title": "Beautiful texture",
            "body": "Love the texture and softness. The only reason for 4 stars is that the bundles were slightly shorter than expected. Otherwise, great quality!",
            "verified_purchase": True,
            "helpful_count": 7,
            "review_date": "2025-11-28",
        },
    },
    {
        "slug": "review-diamond-brazilian-straight",
        "title": "Silky smooth perfection",
        "status": "published",
        "data": {
            "product_id": "brazilian-straight-bundle",
            "customer_name": "Diamond R.",
            "customer_email": "diamond.r@example.com",
            "rating": 5,
            "title": "Silky smooth perfection",
            "body": "This straight hair is incredible! So soft, no tangles, and it blends perfectly with my natural hair. Worth every penny!",
            "verified_purchase": True,
            "helpful_count": 20,
            "review_date": "2025-12-02",
        },
    },
    {
        "slug": "review-asia-brazilian-straight",
        "title": "Good quality hair",
        "status": "published",
        "data": {
            "product_id": "brazilian-straight-bundle",
            "customer_name": "Asia M.",
            "customer_email": "asia.m@example.com",
            "rating": 4,
            "title": "Good quality hair",
            "body": "Nice quality overall. Minimal shedding and holds style well. Would recommend for anyone looking for straight bundles.",
            "verified_purchase": True,
            "helpful_count": 6,
            "review_date": "2025-11-25",
        },
    },
    {
        "slug": "review-crystal-hd-lace-wig",
        "title": "Most natural looking wig!",
        "status": "published",
        "data": {
            "product_id": "brazilian-body-wave-hd-lace-wig",
            "customer_name": "Crystal D.",
            "customer_email": "crystal.d@example.com",
            "rating": 5,
            "title": "Most natural looking wig!",
            "body": "The HD lace literally disappears on my skin! Installation was easy and I've gotten so many compliments. This is now my go-to wig.",
            "verified_purchase": True,
            "helpful_count": 25,
            "review_date": "2025-12-03",
        },
    },
    {
        "slug": "review-monique-hd-lace-wig",
        "title": "Love the pre-plucked hairline",
        "status": "published",
        "data": {
            "product_id": "brazilian-body-wave-hd-lace-wig",
            "customer_name": "Monique B.",
            "customer_email": "monique.b@example.com",
            "rating": 5,
            "title": "Love the pre-plucked hairline",
            "body": "Finally a wig that doesn't need hours of customization! The hairline looks natural right out of the box. Highly recommend!",
            "verified_purchase": True,
            "helpful_count": 18,
            "review_date": "2025-11-29",
        },
    },
]

db = SessionLocal()
try:
    # Get the product_review content type
    ct = db.query(ContentType).filter(ContentType.api_id == "product_review").first()
    if not ct:
        print("ERROR: product_review content type not found!")
        sys.exit(1)

    print(f"Found content type: {ct.name} (ID: {ct.id})")

    # Get a user for author_id
    user = db.query(User).first()
    if not user:
        print("ERROR: No user found!")
        sys.exit(1)

    print(f"Using author: {user.email}")

    created = 0
    skipped = 0

    for review in REVIEWS:
        # Check if already exists
        existing = (
            db.query(ContentEntry)
            .filter(ContentEntry.slug == review["slug"], ContentEntry.content_type_id == ct.id)
            .first()
        )

        if existing:
            print(f"⚠ Already exists: {review['slug']}")
            skipped += 1
            continue

        # Create entry
        entry = ContentEntry(
            id=str(uuid.uuid4()),
            content_type_id=ct.id,
            slug=review["slug"],
            title=review["title"],
            status=review["status"],
            data=json.dumps(review["data"]),
            author_id=user.id,
            version=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(entry)
        print(f"✓ Created: {review['slug']}")
        created += 1

    db.commit()
    print(f"\n✅ Done! Created: {created}, Skipped: {skipped}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback

    traceback.print_exc()
    db.rollback()
finally:
    db.close()
