#!/usr/bin/env python3
"""
Setup script for a killer ecommerce application with Bakalr CMS

This script creates:
- Content types: Product, Category, Brand, Review, Collection
- Sample content: Products, categories, brands
- Relationships between entities
- Media for product images
"""

import asyncio
import sys

import httpx

# API Configuration
API_BASE = "http://localhost:8000/api/v1"
EMAIL = "bsakweson@gmail.com"
PASSWORD = "Angelbenise123!@#"  # Try common default passwords


class EcommerceSetup:
    def __init__(self):
        self.token = None
        self.org_id = None
        self.client = httpx.AsyncClient(timeout=30.0)

    async def login(self):
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
                return False

        except Exception as e:
            print(f"❌ Login error: {e}")
            return False

    async def register_admin(self):
        """Register admin user if login fails"""
        print("📝 Registering admin user...")

        try:
            response = await self.client.post(
                f"{API_BASE}/auth/register",
                json={
                    "email": EMAIL,
                    "password": PASSWORD,
                    "full_name": "Admin User",
                    "organization_name": "Bakalr Boutique",
                },
            )

            if response.status_code in [200, 201]:
                data = response.json()
                self.token = data["access_token"]
                self.org_id = data.get("organization_id")
                print(f"✅ Admin registered (Org ID: {self.org_id})")
                return True
            else:
                print(f"❌ Registration failed: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Registration error: {e}")
            return False

    def headers(self):
        """Get authorization headers"""
        return {"Authorization": f"Bearer {self.token}"}

    async def create_content_type(self, name, slug, schema, description=""):
        """Create a content type"""
        print(f"📋 Creating content type: {name}...")

        # Convert schema dict to fields list format expected by API
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
            if "validation" in field_props:
                field_obj["validation"] = field_props["validation"]
            if "help_text" in field_props or "description" in field_props:
                field_obj["help_text"] = field_props.get("help_text") or field_props.get(
                    "description"
                )

            fields.append(field_obj)

        try:
            response = await self.client.post(
                f"{API_BASE}/content/types",
                headers=self.headers(),
                json={"name": name, "api_id": slug, "fields": fields, "description": description},
            )

            if response.status_code in [200, 201]:
                data = response.json()
                print(f"✅ Created: {name} (ID: {data['id']})")
                return data
            else:
                print(f"⚠️  {name} might already exist: {response.text}")
                # Try to get existing
                response = await self.client.get(
                    f"{API_BASE}/content/types", headers=self.headers()
                )
                if response.status_code == 200:
                    types = response.json()
                    for ct in types:
                        if ct.get("api_id") == slug:
                            print(f"✅ Using existing: {name} (ID: {ct['id']})")
                            return ct
                return None

        except Exception as e:
            print(f"❌ Error creating {name}: {e}")
            return None

    async def create_content(self, content_type_id, title, slug, fields, status="published"):
        """Create a content entry"""
        try:
            response = await self.client.post(
                f"{API_BASE}/content/entries",
                headers=self.headers(),
                json={
                    "content_type_id": content_type_id,
                    "data": fields,
                    "slug": slug,
                    "status": status,
                },
            )

            if response.status_code in [200, 201]:
                data = response.json()
                print(f"  ✅ Created: {title}")
                return data
            else:
                print(f"  ⚠️  Failed to create {title}: {response.text}")
                return None

        except Exception as e:
            print(f"  ❌ Error creating {title}: {e}")
            return None

    async def setup_content_types(self):
        """Create all ecommerce content types"""
        print("\n📦 Creating E-commerce Content Types...")

        # 1. Category Content Type
        category_ct = await self.create_content_type(
            name="Category",
            slug="category",
            description="Product categories for organizing items",
            schema={
                "name": {
                    "type": "text",
                    "required": True,
                    "label": "Category Name",
                    "description": "The display name of the category",
                },
                "description": {
                    "type": "textarea",
                    "label": "Description",
                    "description": "Category description for SEO",
                },
                "slug": {"type": "text", "required": True, "label": "URL Slug"},
                "image": {"type": "image", "label": "Category Image"},
                "parent_category": {
                    "type": "text",
                    "label": "Parent Category",
                    "description": "For nested categories",
                },
                "display_order": {
                    "type": "number",
                    "label": "Display Order",
                    "description": "Order in which to display",
                },
                "is_featured": {"type": "boolean", "label": "Featured Category"},
            },
        )

        # 2. Brand Content Type
        brand_ct = await self.create_content_type(
            name="Brand",
            slug="brand",
            description="Product brands and manufacturers",
            schema={
                "name": {"type": "text", "required": True, "label": "Brand Name"},
                "description": {"type": "richtext", "label": "Brand Story"},
                "logo": {"type": "image", "label": "Brand Logo"},
                "website": {"type": "url", "label": "Website"},
                "country": {"type": "text", "label": "Country of Origin"},
                "is_featured": {"type": "boolean", "label": "Featured Brand"},
            },
        )

        # 3. Product Content Type
        product_ct = await self.create_content_type(
            name="Product",
            slug="product",
            description="E-commerce products",
            schema={
                "name": {"type": "text", "required": True, "label": "Product Name"},
                "description": {
                    "type": "richtext",
                    "required": True,
                    "label": "Product Description",
                },
                "short_description": {
                    "type": "textarea",
                    "label": "Short Description",
                    "description": "Brief description for listings",
                },
                "sku": {
                    "type": "text",
                    "required": True,
                    "label": "SKU",
                    "description": "Stock Keeping Unit",
                },
                "price": {
                    "type": "number",
                    "required": True,
                    "label": "Price",
                    "description": "Regular price",
                },
                "sale_price": {
                    "type": "number",
                    "label": "Sale Price",
                    "description": "Discounted price (optional)",
                },
                "cost": {
                    "type": "number",
                    "label": "Cost",
                    "description": "Cost price for margin calculation",
                },
                "currency": {
                    "type": "select",
                    "label": "Currency",
                    "options": ["USD", "EUR", "GBP", "CAD", "AUD"],
                },
                "stock_quantity": {"type": "number", "label": "Stock Quantity"},
                "stock_status": {
                    "type": "select",
                    "label": "Stock Status",
                    "options": ["in_stock", "out_of_stock", "backorder", "discontinued"],
                },
                "category": {
                    "type": "text",
                    "label": "Category",
                    "description": "Primary category",
                },
                "brand": {"type": "text", "label": "Brand"},
                "images": {
                    "type": "text",
                    "label": "Product Images",
                    "description": "Comma-separated image URLs",
                },
                "featured_image": {"type": "image", "label": "Featured Image"},
                "weight": {"type": "number", "label": "Weight (kg)"},
                "dimensions": {
                    "type": "text",
                    "label": "Dimensions",
                    "description": "L x W x H in cm",
                },
                "tags": {"type": "text", "label": "Tags", "description": "Comma-separated tags"},
                "is_featured": {"type": "boolean", "label": "Featured Product"},
                "is_new": {"type": "boolean", "label": "New Arrival"},
                "is_on_sale": {"type": "boolean", "label": "On Sale"},
                "rating": {"type": "number", "label": "Average Rating", "description": "1-5 stars"},
                "review_count": {"type": "number", "label": "Number of Reviews"},
                "specifications": {
                    "type": "textarea",
                    "label": "Specifications",
                    "description": "JSON or formatted specifications",
                },
            },
        )

        # 4. Collection Content Type
        collection_ct = await self.create_content_type(
            name="Collection",
            slug="collection",
            description="Curated product collections",
            schema={
                "name": {"type": "text", "required": True, "label": "Collection Name"},
                "description": {"type": "richtext", "label": "Description"},
                "slug": {"type": "text", "required": True, "label": "URL Slug"},
                "banner_image": {"type": "image", "label": "Banner Image"},
                "products": {
                    "type": "text",
                    "label": "Product IDs",
                    "description": "Comma-separated product IDs",
                },
                "is_featured": {"type": "boolean", "label": "Featured Collection"},
                "display_order": {"type": "number", "label": "Display Order"},
            },
        )

        # 5. Review Content Type
        review_ct = await self.create_content_type(
            name="Review",
            slug="review",
            description="Product reviews and ratings",
            schema={
                "product_id": {"type": "text", "required": True, "label": "Product ID"},
                "customer_name": {"type": "text", "required": True, "label": "Customer Name"},
                "customer_email": {"type": "email", "label": "Customer Email"},
                "rating": {
                    "type": "number",
                    "required": True,
                    "label": "Rating",
                    "description": "1-5 stars",
                },
                "title": {"type": "text", "label": "Review Title"},
                "comment": {"type": "textarea", "required": True, "label": "Review Comment"},
                "verified_purchase": {"type": "boolean", "label": "Verified Purchase"},
                "helpful_count": {
                    "type": "number",
                    "label": "Helpful Count",
                    "description": "Number of helpful votes",
                },
            },
        )

        return {
            "category": category_ct,
            "brand": brand_ct,
            "product": product_ct,
            "collection": collection_ct,
            "review": review_ct,
        }

    async def create_sample_data(self, content_types):
        """Create sample ecommerce data"""
        print("\n🎨 Creating Sample E-commerce Data...")

        if (
            not content_types.get("category")
            or not content_types.get("brand")
            or not content_types.get("product")
        ):
            print("❌ Content types not created, skipping sample data")
            return

        # Create Categories
        print("\n📂 Creating Categories...")
        categories = []
        cat_data = [
            {
                "name": "Electronics",
                "slug": "electronics",
                "description": "Electronic devices and accessories",
                "display_order": 1,
                "is_featured": True,
            },
            {
                "name": "Clothing",
                "slug": "clothing",
                "description": "Fashion and apparel",
                "display_order": 2,
                "is_featured": True,
            },
            {
                "name": "Home & Garden",
                "slug": "home-garden",
                "description": "Home decor and garden supplies",
                "display_order": 3,
                "is_featured": False,
            },
            {
                "name": "Sports",
                "slug": "sports",
                "description": "Sports equipment and activewear",
                "display_order": 4,
                "is_featured": True,
            },
            {
                "name": "Books",
                "slug": "books",
                "description": "Books and magazines",
                "display_order": 5,
                "is_featured": False,
            },
        ]

        for cat in cat_data:
            result = await self.create_content(
                content_types["category"]["id"], title=cat["name"], slug=cat["slug"], fields=cat
            )
            if result:
                categories.append(result)

        # Create Brands
        print("\n🏷️  Creating Brands...")
        brands = []
        brand_data = [
            {
                "name": "TechPro",
                "description": "Leading technology brand",
                "country": "USA",
                "is_featured": True,
            },
            {
                "name": "StyleCo",
                "description": "Premium fashion brand",
                "country": "France",
                "is_featured": True,
            },
            {
                "name": "HomeEssentials",
                "description": "Quality home goods",
                "country": "Germany",
                "is_featured": False,
            },
            {
                "name": "ActiveLife",
                "description": "Sports and fitness gear",
                "country": "USA",
                "is_featured": True,
            },
        ]

        for brand in brand_data:
            result = await self.create_content(
                content_types["brand"]["id"],
                title=brand["name"],
                slug=brand["name"].lower().replace(" ", "-"),
                fields=brand,
            )
            if result:
                brands.append(result)

        # Create Products
        print("\n🛍️  Creating Products...")
        products = []
        product_data = [
            {
                "name": "Wireless Bluetooth Headphones",
                "slug": "wireless-bluetooth-headphones",
                "short_description": "Premium noise-canceling headphones with 30hr battery",
                "description": "<p>Experience crystal-clear audio with our premium wireless headphones. Features active noise cancellation, 30-hour battery life, and comfortable over-ear design.</p>",
                "sku": "TECH-WH-001",
                "price": 149.99,
                "sale_price": 129.99,
                "cost": 75.00,
                "currency": "USD",
                "stock_quantity": 50,
                "stock_status": "in_stock",
                "category": "Electronics",
                "brand": "TechPro",
                "weight": 0.3,
                "dimensions": "20 x 18 x 8",
                "tags": "audio, wireless, headphones, bluetooth",
                "is_featured": True,
                "is_new": True,
                "is_on_sale": True,
                "rating": 4.5,
                "review_count": 124,
                "specifications": '{"battery": "30 hours", "bluetooth": "5.0", "anc": "Yes", "color": "Black"}',
            },
            {
                "name": "Classic Cotton T-Shirt",
                "slug": "classic-cotton-tshirt",
                "short_description": "100% organic cotton, comfortable fit",
                "description": "<p>Our classic t-shirt is made from 100% organic cotton for ultimate comfort. Available in multiple colors and sizes.</p>",
                "sku": "CLOTH-TS-001",
                "price": 29.99,
                "currency": "USD",
                "stock_quantity": 200,
                "stock_status": "in_stock",
                "category": "Clothing",
                "brand": "StyleCo",
                "weight": 0.2,
                "tags": "clothing, tshirt, cotton, casual",
                "is_featured": False,
                "is_new": False,
                "is_on_sale": False,
                "rating": 4.8,
                "review_count": 89,
                "specifications": '{"material": "100% Cotton", "fit": "Regular", "care": "Machine washable"}',
            },
            {
                "name": "Smart Fitness Watch",
                "slug": "smart-fitness-watch",
                "short_description": "Track your fitness goals with precision",
                "description": "<p>Advanced fitness tracking with heart rate monitor, GPS, and 7-day battery life. Water resistant up to 50m.</p>",
                "sku": "TECH-SW-001",
                "price": 249.99,
                "cost": 125.00,
                "currency": "USD",
                "stock_quantity": 30,
                "stock_status": "in_stock",
                "category": "Electronics",
                "brand": "TechPro",
                "weight": 0.05,
                "dimensions": "4 x 4 x 1",
                "tags": "fitness, smartwatch, health, tracking",
                "is_featured": True,
                "is_new": True,
                "is_on_sale": False,
                "rating": 4.6,
                "review_count": 67,
                "specifications": '{"battery": "7 days", "waterproof": "50m", "gps": "Yes", "heart_rate": "Yes"}',
            },
            {
                "name": "Yoga Mat Premium",
                "slug": "yoga-mat-premium",
                "short_description": "Non-slip, eco-friendly yoga mat",
                "description": "<p>Premium yoga mat made from eco-friendly materials. Extra thick for comfort, non-slip surface for safety.</p>",
                "sku": "SPORT-YM-001",
                "price": 49.99,
                "sale_price": 39.99,
                "currency": "USD",
                "stock_quantity": 75,
                "stock_status": "in_stock",
                "category": "Sports",
                "brand": "ActiveLife",
                "weight": 1.2,
                "dimensions": "180 x 60 x 0.6",
                "tags": "yoga, fitness, mat, exercise",
                "is_featured": True,
                "is_new": False,
                "is_on_sale": True,
                "rating": 4.7,
                "review_count": 156,
                "specifications": '{"material": "TPE", "thickness": "6mm", "eco_friendly": "Yes"}',
            },
            {
                "name": "Leather Laptop Bag",
                "slug": "leather-laptop-bag",
                "short_description": 'Genuine leather, fits 15" laptop',
                "description": "<p>Stylish and durable leather laptop bag. Multiple compartments for organization, padded laptop section.</p>",
                "sku": "ACC-LB-001",
                "price": 119.99,
                "currency": "USD",
                "stock_quantity": 25,
                "stock_status": "in_stock",
                "category": "Electronics",
                "brand": "StyleCo",
                "weight": 0.8,
                "dimensions": "40 x 30 x 10",
                "tags": "laptop, bag, leather, business",
                "is_featured": False,
                "is_new": False,
                "is_on_sale": False,
                "rating": 4.4,
                "review_count": 42,
                "specifications": '{"material": "Genuine Leather", "laptop_size": "15 inch", "pockets": "Multiple"}',
            },
        ]

        for prod in product_data:
            result = await self.create_content(
                content_types["product"]["id"], title=prod["name"], slug=prod["slug"], fields=prod
            )
            if result:
                products.append(result)

        print(
            f"\n✅ Created {len(categories)} categories, {len(brands)} brands, and {len(products)} products!"
        )
        return {"categories": categories, "brands": brands, "products": products}

    async def run(self):
        """Run the complete setup"""
        print("=" * 60)
        print("🎂 Bakalr CMS - E-commerce Setup")
        print("=" * 60)

        # Try to login first
        if not await self.login():
            # If login fails, try to register
            if not await self.register_admin():
                print("\n❌ Setup failed: Could not login or register")
                return False

        # Create content types
        content_types = await self.setup_content_types()

        # Create sample data
        await self.create_sample_data(content_types)

        print("\n" + "=" * 60)
        print("✅ E-commerce Setup Complete!")
        print("=" * 60)
        print("\n📍 Next Steps:")
        print("  • View API docs: http://localhost:8000/api/docs")
        print("  • View frontend: http://localhost:3000/dashboard")
        print("  • Manage content: http://localhost:3000/dashboard/content")
        print("\n🛍️  Sample Data Created:")
        print("  • 5 Product Categories")
        print("  • 4 Brands")
        print("  • 5 Sample Products")
        print("\n💡 Tips:")
        print("  • Add product images via Media section")
        print("  • Create product relationships")
        print("  • Set up search with Meilisearch")
        print("  • Configure webhooks for inventory updates")

        await self.client.aclose()
        return True


async def main():
    setup = EcommerceSetup()
    success = await setup.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
