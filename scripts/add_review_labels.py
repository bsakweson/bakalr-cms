#!/usr/bin/env python3
"""
Add review labels to site settings for content-driven reviews page.
Run with: cat scripts/add_review_labels.py | docker exec -i bakalr-backend python3 -
"""

import os
import sys

sys.path.insert(0, "/app")
os.chdir("/app")

import json

from backend.api.content import auto_translate_entry_background
from backend.db.session import SessionLocal
from backend.models.content import ContentEntry, ContentType
from backend.models.translation import Translation

SITE_SETTINGS_ID = "34850f0b-d781-4adf-94be-453461f5227e"

REVIEW_LABELS = {
    "reviews": {
        "title": "Customer Reviews",
        "rating_breakdown": "Rating Breakdown",
        "write_review": "Write a Review",
        "verified_purchase": "Verified Purchase",
        "helpful": "Helpful",
        "most_recent": "Most Recent",
        "highest_rated": "Highest Rated",
        "lowest_rated": "Lowest Rated",
        "out_of": "out of",
        "customer_reviews": "customer reviews",
        "star": "star",
        "stars": "stars",
        "view_product": "View Product",
        "no_reviews": "No reviews yet. Be the first to review this product!",
        "load_more": "Load More Reviews",
        "showing": "Showing",
        "of": "of",
        "reviews_label": "reviews",
    }
}

db = SessionLocal()
try:
    entry = db.query(ContentEntry).filter(ContentEntry.id == SITE_SETTINGS_ID).first()
    if entry:
        data = json.loads(entry.data) if isinstance(entry.data, str) else entry.data

        # Add review labels to common_labels
        if "common_labels" not in data:
            data["common_labels"] = {}

        data["common_labels"]["reviews"] = REVIEW_LABELS["reviews"]

        entry.data = json.dumps(data)

        # Delete existing translations to force regeneration
        deleted = (
            db.query(Translation).filter(Translation.content_entry_id == SITE_SETTINGS_ID).delete()
        )

        db.commit()
        print(f"Added review labels to site settings. Deleted {deleted} old translations.")

        # Trigger auto-translation
        ct = db.query(ContentType).filter(ContentType.id == entry.content_type_id).first()
        if ct:
            auto_translate_entry_background(entry.id, ct.organization_id, db)
            print("Triggered auto-translation for all locales.")

        print("\nReview labels added:")
        for key, value in REVIEW_LABELS["reviews"].items():
            print(f"  {key}: {value}")
    else:
        print(f"Site settings entry not found: {SITE_SETTINGS_ID}")
finally:
    db.close()
