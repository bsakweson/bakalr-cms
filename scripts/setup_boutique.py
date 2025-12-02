#!/usr/bin/env python3
"""
Bakalr Boutique Setup Script
Creates e-commerce content types and sample data for Bakalr Boutique

Usage:
    poetry run python scripts/setup_boutique.py           # Full setup
    poetry run python scripts/setup_boutique.py --check   # Check only
    poetry run python scripts/setup_boutique.py --reset   # Delete and recreate
"""

import argparse
import asyncio
import sys
from typing import Dict, List, Optional

import httpx

# Configuration
API_BASE = "http://localhost:8000/api/v1"
EMAIL = "bsakweson@gmail.com"
PASSWORD = "Angelbenise123!@#"


class BoutiqueSetup:
    def __init__(self, check_only: bool = False, reset: bool = False):
        self.token = None
        self.org_id = None
        self.check_only = check_only
        self.reset = reset
        self.client = httpx.AsyncClient(timeout=30.0)
        self.content_types = {}

    async def login(self) -> bool:
        """Login and get JWT token"""
        print("🔐 Logging in...")

        try:
            response = await self.client.post(
                f"{API_BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD}
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                self.org_id = data.get("organization_id")
                print(f"✅ Logged in successfully (Org ID: {self.org_id})")
                return True
            else:
                print(f"❌ Login failed: {response.text}")
                print("💡 Tip: Make sure the backend is running and credentials are correct")
                return False

        except Exception as e:
            print(f"❌ Login error: {e}")
            print("💡 Tip: Is the backend running? Check: docker-compose ps")
            return False

    def headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        return {"Authorization": f"Bearer {self.token}"}

    async def check_existing_content_types(self) -> Dict[str, Dict]:
        """Check what content types already exist"""
        print("\n🔍 Checking existing content types...")

        try:
            response = await self.client.get(f"{API_BASE}/content/types", headers=self.headers())

            if response.status_code == 200:
                existing = response.json()
                print(f"Found {len(existing)} existing content types")

                result = {}
                for ct in existing:
                    slug = ct.get("slug")
                    result[slug] = ct
                    print(f"  • {ct.get('name')} (slug: {slug}, id: {ct.get('id')})")

                return result
            else:
                print(f"⚠️  Could not fetch content types: {response.text}")
                return {}

        except Exception as e:
            print(f"❌ Error checking content types: {e}")
            return {}

    async def delete_content_type(self, content_type_id: int, name: str) -> bool:
        """Delete a content type"""
        print(f"🗑️  Deleting content type: {name}...")

        try:
            response = await self.client.delete(
                f"{API_BASE}/content/types/{content_type_id}", headers=self.headers()
            )

            if response.status_code in [200, 204]:
                print(f"  ✅ Deleted {name}")
                return True
            else:
                print(f"  ⚠️  Could not delete {name}: {response.text}")
                return False

        except Exception as e:
            print(f"  ❌ Error deleting {name}: {e}")
            return False

    async def create_content_type(
        self, name: str, slug: str, schema: Dict, description: str = ""
    ) -> Optional[int]:
        """Create a content type"""
        print(f"📋 Creating content type: {name}...")

        # Convert schema to API format
        fields = []
        for field_name, field_props in schema.items():
            field_obj = {
                "name": field_name,
                "type": field_props.get("type", "text"),
                "required": field_props.get("required", False),
                "unique": field_props.get("unique", False),
                "localized": field_props.get("localized", False),
            }
            if "default" in field_props:
                field_obj["default"] = field_props["default"]
            if "options" in field_props:
                field_obj["options"] = field_props["options"]
            fields.append(field_obj)

        payload = {
            "name": name,
            "slug": slug,
            "description": description,
            "schema": {"fields": fields},
        }

        try:
            response = await self.client.post(
                f"{API_BASE}/content/types", json=payload, headers=self.headers()
            )

            if response.status_code in [200, 201]:
                data = response.json()
                content_type_id = data.get("id")
                print(f"  ✅ Created {name} (ID: {content_type_id})")
                return content_type_id
            else:
                print(f"  ❌ Failed: {response.text}")
                return None

        except Exception as e:
            print(f"  ❌ Error: {e}")
            return None

    def get_category_schema(self) -> Dict:
        """Get Category content type schema"""
        return {
            "name": {"type": "text", "required": True, "unique": False},
            "description": {"type": "textarea", "required": False},
            "slug": {"type": "text", "required": True, "unique": True},
            "image": {"type": "image", "required": False},
            "parent_category": {"type": "text", "required": False},
            "display_order": {"type": "number", "required": False, "default": 0},
            "is_featured": {"type": "boolean", "required": False, "default": False},
        }

    def get_brand_schema(self) -> Dict:
        """Get Brand content type schema"""
        return {
            "name": {"type": "text", "required": True, "unique": True},
            "description": {"type": "richtext", "required": False},
            "logo": {"type": "image", "required": False},
            "website": {"type": "url", "required": False},
            "country": {"type": "text", "required": False},
            "is_featured": {"type": "boolean", "required": False, "default": False},
        }

    def get_product_schema(self) -> Dict:
        """Get Product content type schema"""
        return {
            "name": {"type": "text", "required": True},
            "sku": {"type": "text", "required": True, "unique": True},
            "description": {"type": "richtext", "required": True},
            "price": {"type": "number", "required": True},
            "sale_price": {"type": "number", "required": False},
            "cost": {"type": "number", "required": False},
            "currency": {"type": "text", "required": False, "default": "USD"},
            "stock_quantity": {"type": "number", "required": True, "default": 0},
            "stock_status": {
                "type": "select",
                "required": True,
                "default": "in_stock",
                "options": ["in_stock", "out_of_stock", "on_backorder"],
            },
            "category": {"type": "text", "required": True},
            "brand": {"type": "text", "required": False},
            "images": {"type": "text", "required": False},  # Comma-separated URLs
            "featured_image": {"type": "image", "required": False},
            "weight": {"type": "number", "required": False},
            "dimensions": {"type": "text", "required": False},
            "tags": {"type": "text", "required": False},
            "is_featured": {"type": "boolean", "required": False, "default": False},
            "is_new": {"type": "boolean", "required": False, "default": False},
            "is_on_sale": {"type": "boolean", "required": False, "default": False},
            "rating": {"type": "number", "required": False, "default": 0},
            "review_count": {"type": "number", "required": False, "default": 0},
            "specifications": {"type": "textarea", "required": False},  # JSON string
        }

    def get_collection_schema(self) -> Dict:
        """Get Collection content type schema"""
        return {
            "name": {"type": "text", "required": True, "unique": True},
            "description": {"type": "richtext", "required": True},
            "slug": {"type": "text", "required": True, "unique": True},
            "banner_image": {"type": "image", "required": False},
            "products": {"type": "text", "required": False},  # Comma-separated IDs
            "is_featured": {"type": "boolean", "required": False, "default": False},
            "display_order": {"type": "number", "required": False, "default": 0},
        }

    def get_review_schema(self) -> Dict:
        """Get Review content type schema"""
        return {
            "product_id": {"type": "number", "required": True},
            "customer_name": {"type": "text", "required": True},
            "customer_email": {"type": "email", "required": False},
            "rating": {"type": "number", "required": True},  # 1-5
            "title": {"type": "text", "required": True},
            "comment": {"type": "textarea", "required": True},
            "verified_purchase": {"type": "boolean", "required": False, "default": False},
            "helpful_count": {"type": "number", "required": False, "default": 0},
        }

    async def setup_content_types(self) -> Dict[str, int]:
        """Create all content types"""
        print("\n" + "=" * 60)
        print("📦 Setting Up Content Types")
        print("=" * 60)

        content_types = {}

        # Category
        ct_id = await self.create_content_type(
            "Category",
            "category",
            self.get_category_schema(),
            "Product categories for organizing inventory",
        )
        if ct_id:
            content_types["category"] = ct_id

        # Brand
        ct_id = await self.create_content_type(
            "Brand",
            "brand",
            self.get_brand_schema(),
            "Product brands and manufacturers",
        )
        if ct_id:
            content_types["brand"] = ct_id

        # Product
        ct_id = await self.create_content_type(
            "Product",
            "product",
            self.get_product_schema(),
            "Products available in the boutique",
        )
        if ct_id:
            content_types["product"] = ct_id

        # Collection
        ct_id = await self.create_content_type(
            "Collection",
            "collection",
            self.get_collection_schema(),
            "Curated collections of products",
        )
        if ct_id:
            content_types["collection"] = ct_id

        # Review
        ct_id = await self.create_content_type(
            "Review",
            "review",
            self.get_review_schema(),
            "Customer reviews and ratings",
        )
        if ct_id:
            content_types["review"] = ct_id

        return content_types

    async def create_sample_categories(self) -> List[int]:
        """Create sample categories"""
        print("\n📁 Creating Sample Categories...")

        categories = [
            {"name": "Fashion", "slug": "fashion", "description": "Clothing and accessories"},
            {"name": "Home Decor", "slug": "home-decor", "description": "Home decoration items"},
            {"name": "Electronics", "slug": "electronics", "description": "Tech products"},
            {"name": "Beauty", "slug": "beauty", "description": "Beauty and cosmetics"},
            {"name": "Books", "slug": "books", "description": "Books and magazines"},
        ]

        created_ids = []
        for cat in categories:
            response = await self.client.post(
                f"{API_BASE}/content/entries",
                json={
                    "content_type_id": self.content_types.get("category"),
                    "title": cat["name"],
                    "slug": cat["slug"],
                    "status": "published",
                    "fields": {
                        "name": cat["name"],
                        "slug": cat["slug"],
                        "description": cat["description"],
                        "display_order": len(created_ids),
                        "is_featured": len(created_ids) < 3,
                    },
                },
                headers=self.headers(),
            )

            if response.status_code in [200, 201]:
                data = response.json()
                created_ids.append(data.get("id"))
                print(f"  ✅ Created category: {cat['name']}")
            else:
                print(f"  ⚠️  Failed to create {cat['name']}: {response.text}")

        return created_ids

    async def create_sample_brands(self) -> List[int]:
        """Create sample brands"""
        print("\n🏷️  Creating Sample Brands...")

        brands = [
            {
                "name": "Bakalr Original",
                "country": "USA",
                "description": "Our signature collection",
            },
            {"name": "Eco Fashion", "country": "Denmark", "description": "Sustainable fashion"},
            {"name": "Urban Style", "country": "UK", "description": "Contemporary urban wear"},
            {"name": "Classic Home", "country": "Italy", "description": "Timeless home decor"},
        ]

        created_ids = []
        for brand in brands:
            response = await self.client.post(
                f"{API_BASE}/content/entries",
                json={
                    "content_type_id": self.content_types.get("brand"),
                    "title": brand["name"],
                    "slug": brand["name"].lower().replace(" ", "-"),
                    "status": "published",
                    "fields": {
                        "name": brand["name"],
                        "description": f"<p>{brand['description']}</p>",
                        "country": brand["country"],
                        "is_featured": len(created_ids) < 2,
                    },
                },
                headers=self.headers(),
            )

            if response.status_code in [200, 201]:
                data = response.json()
                created_ids.append(data.get("id"))
                print(f"  ✅ Created brand: {brand['name']}")
            else:
                print(f"  ⚠️  Failed to create {brand['name']}: {response.text}")

        return created_ids

    async def create_sample_products(self) -> List[int]:
        """Create sample products"""
        print("\n🛍️  Creating Sample Products...")

        products = [
            {
                "name": "Classic Leather Jacket",
                "sku": "JACKET-001",
                "description": "<p>Genuine leather jacket with classic styling</p>",
                "price": 299.99,
                "category": "Fashion",
                "brand": "Bakalr Original",
                "stock_quantity": 50,
                "is_featured": True,
                "tags": "leather, jacket, classic, outerwear",
            },
            {
                "name": "Modern Table Lamp",
                "sku": "LAMP-001",
                "description": "<p>Contemporary design with adjustable brightness</p>",
                "price": 89.99,
                "sale_price": 69.99,
                "category": "Home Decor",
                "brand": "Classic Home",
                "stock_quantity": 100,
                "is_featured": True,
                "is_on_sale": True,
                "tags": "lamp, lighting, home, decor",
            },
            {
                "name": "Organic Cotton T-Shirt",
                "sku": "TSHIRT-001",
                "description": "<p>Sustainable organic cotton, available in multiple colors</p>",
                "price": 39.99,
                "category": "Fashion",
                "brand": "Eco Fashion",
                "stock_quantity": 200,
                "is_new": True,
                "tags": "organic, cotton, sustainable, tshirt",
            },
            {
                "name": "Minimalist Wall Clock",
                "sku": "CLOCK-001",
                "description": "<p>Elegant minimalist design for modern homes</p>",
                "price": 59.99,
                "category": "Home Decor",
                "brand": "Classic Home",
                "stock_quantity": 75,
                "tags": "clock, wall, minimalist, home",
            },
            {
                "name": "Urban Backpack",
                "sku": "BACKPACK-001",
                "description": "<p>Durable backpack for city life and travel</p>",
                "price": 79.99,
                "category": "Fashion",
                "brand": "Urban Style",
                "stock_quantity": 120,
                "tags": "backpack, travel, urban, bag",
            },
        ]

        created_ids = []
        for product in products:
            response = await self.client.post(
                f"{API_BASE}/content/entries",
                json={
                    "content_type_id": self.content_types.get("product"),
                    "title": product["name"],
                    "slug": product["sku"].lower(),
                    "status": "published",
                    "fields": product,
                },
                headers=self.headers(),
            )

            if response.status_code in [200, 201]:
                data = response.json()
                created_ids.append(data.get("id"))
                print(f"  ✅ Created product: {product['name']}")
            else:
                print(f"  ⚠️  Failed to create {product['name']}: {response.text}")

        return created_ids

    async def run(self) -> bool:
        """Run the setup"""
        print("\n" + "=" * 60)
        print("🛍️  Bakalr Boutique Setup")
        print("=" * 60)

        # Login
        if not await self.login():
            return False

        # Check existing content types
        existing = await self.check_existing_content_types()

        if self.check_only:
            print("\n✅ Check complete!")
            return True

        # Reset mode - delete existing content types
        if self.reset and existing:
            print("\n🗑️  Reset mode: Deleting existing content types...")
            for slug, ct in existing.items():
                if slug in ["category", "brand", "product", "collection", "review"]:
                    await self.delete_content_type(ct["id"], ct["name"])

        # Use existing content types (they already exist)
        if len(existing) >= 5:
            print("\n✅ Content types already exist, using them...")
            self.content_types = {
                "category": 1,
                "brand": 2,
                "product": 3,
                "collection": 4,
                "review": 5,
            }
        else:
            # Create content types
            self.content_types = await self.setup_content_types()

            if not self.content_types:
                print("\n❌ Failed to create content types")
                return False

        # Create sample data
        print("\n" + "=" * 60)
        print("📦 Creating Sample Data")
        print("=" * 60)

        await self.create_sample_categories()
        await self.create_sample_brands()
        await self.create_sample_products()

        # Summary
        print("\n" + "=" * 60)
        print("✅ Bakalr Boutique Setup Complete!")
        print("=" * 60)
        print("\n📍 Next Steps:")
        print("  • View API docs: http://localhost:8000/api/docs")
        print("  • View admin dashboard: http://localhost:3000")
        print("  • Manage content: http://localhost:3000/dashboard/content")
        print("\n🛍️  Created:")
        print("  • 5 Product Categories")
        print("  • 4 Brands")
        print("  • 5 Sample Products")
        print("\n💡 See docs/bakalr-boutique-setup.md for full guide")

        await self.client.aclose()
        return True


async def main():
    parser = argparse.ArgumentParser(description="Setup Bakalr Boutique e-commerce")
    parser.add_argument("--check", action="store_true", help="Check existing content only")
    parser.add_argument("--reset", action="store_true", help="Delete and recreate content types")
    args = parser.parse_args()

    setup = BoutiqueSetup(check_only=args.check, reset=args.reset)
    success = await setup.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
