#!/usr/bin/env python3
"""
Seed product entries for the storefront demo.
Creates sample products with realistic data.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models.content import ContentEntry, ContentType
from backend.models.organization import Organization

# Use localhost instead of 'postgres' for local access
DATABASE_URL = (
    "postgresql://bakalr:5jhVdLjuCFilXf5BveBTB1Ow4lZ9NYScVSzWKvMWPpE@localhost:5432/bakalr_cms"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

SAMPLE_PRODUCTS = [
    {
        "name": "Premium Wireless Headphones",
        "sku": "WH-1000XM5",
        "description": "<p>Experience industry-leading noise cancellation with premium wireless headphones. Perfect for music lovers and frequent travelers.</p>",
        "price": 349.99,
        "images": ["/images/products/headphones-1.jpg"],
        "category": "Electronics",
        "brand": "AudioTech",
        "in_stock": True,
        "stock_quantity": 25,
    },
    {
        "name": "Organic Cotton T-Shirt",
        "sku": "TS-ORG-001",
        "description": "<p>Soft, breathable, and sustainably made. Our organic cotton t-shirt is perfect for everyday wear.</p>",
        "price": 29.99,
        "images": ["/images/products/tshirt-1.jpg"],
        "category": "Clothing",
        "brand": "EcoWear",
        "in_stock": True,
        "stock_quantity": 150,
    },
    {
        "name": "Stainless Steel Water Bottle",
        "sku": "WB-SS-750",
        "description": "<p>Keep your drinks cold for 24 hours or hot for 12 hours with our insulated stainless steel water bottle.</p>",
        "price": 24.99,
        "images": ["/images/products/bottle-1.jpg"],
        "category": "Home & Kitchen",
        "brand": "HydroLife",
        "in_stock": True,
        "stock_quantity": 200,
    },
    {
        "name": "Leather Laptop Bag",
        "sku": "LB-15-BRN",
        "description": "<p>Handcrafted genuine leather laptop bag with multiple compartments. Fits laptops up to 15 inches.</p>",
        "price": 129.99,
        "images": ["/images/products/bag-1.jpg"],
        "category": "Accessories",
        "brand": "LeatherCraft",
        "in_stock": True,
        "stock_quantity": 45,
    },
    {
        "name": "Smart Fitness Watch",
        "sku": "FW-SMART-2024",
        "description": "<p>Track your fitness goals with GPS, heart rate monitoring, sleep tracking, and 50+ sport modes.</p>",
        "price": 199.99,
        "images": ["/images/products/watch-1.jpg"],
        "category": "Electronics",
        "brand": "FitTech",
        "in_stock": True,
        "stock_quantity": 60,
    },
    {
        "name": "Ceramic Coffee Mug Set",
        "sku": "MUG-CER-4PC",
        "description": "<p>Set of 4 handmade ceramic mugs. Dishwasher and microwave safe. Each mug holds 12 oz.</p>",
        "price": 39.99,
        "images": ["/images/products/mug-set-1.jpg"],
        "category": "Home & Kitchen",
        "brand": "Artisan Home",
        "in_stock": True,
        "stock_quantity": 80,
    },
    {
        "name": "Wireless Gaming Mouse",
        "sku": "GM-WL-PRO",
        "description": "<p>High-precision wireless gaming mouse with RGB lighting, 6 programmable buttons, and 20,000 DPI sensor.</p>",
        "price": 79.99,
        "images": ["/images/products/mouse-1.jpg"],
        "category": "Electronics",
        "brand": "GameGear",
        "in_stock": True,
        "stock_quantity": 75,
    },
    {
        "name": "Yoga Mat Premium",
        "sku": "YM-PREM-6MM",
        "description": "<p>Extra-thick 6mm yoga mat with non-slip surface. Includes carrying strap. Perfect for all yoga styles.</p>",
        "price": 49.99,
        "images": ["/images/products/yoga-mat-1.jpg"],
        "category": "Sports & Fitness",
        "brand": "ZenFit",
        "in_stock": True,
        "stock_quantity": 100,
    },
]


def seed_products():
    """Create sample product entries"""
    db = SessionLocal()
    try:
        # Get the first organization
        org = db.query(Organization).first()
        if not org:
            print("❌ No organization found. Please run seed_database.py first.")
            return

        print(f"Using organization: {org.name}")

        # Find or verify Product content type exists
        product_ct = (
            db.query(ContentType)
            .filter(ContentType.api_id == "product", ContentType.organization_id == org.id)
            .first()
        )

        if not product_ct:
            print("❌ Product content type not found. Please run seed_database.py first.")
            return

        print(f"✓ Found Product content type (ID: {product_ct.id})")

        # Check if products already exist
        existing_count = (
            db.query(ContentEntry).filter(ContentEntry.content_type_id == product_ct.id).count()
        )

        if existing_count > 0:
            print(f"ℹ️  {existing_count} product(s) already exist. Skipping seed.")
            return

        # Create products
        print(f"\nCreating {len(SAMPLE_PRODUCTS)} sample products...")
        for i, product_data in enumerate(SAMPLE_PRODUCTS, 1):
            # Generate slug from name
            slug = product_data["name"].lower().replace(" ", "-").replace(",", "")

            entry = ContentEntry(
                content_type_id=product_ct.id,
                title=product_data["name"],
                slug=slug,
                fields_data=json.dumps(product_data),
                status="published",
                organization_id=org.id,
            )
            db.add(entry)
            print(f"  {i}. {product_data['name']} - ${product_data['price']}")

        db.commit()
        print(f"\n✅ Successfully created {len(SAMPLE_PRODUCTS)} products!")
        print("\nView products at: http://localhost:3001/products")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Bakalr CMS - Product Seeding")
    print("=" * 60)
    seed_products()
