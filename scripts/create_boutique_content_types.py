"""
Create content types for Bakalr Boutique migration

This script creates comprehensive e-commerce content types in Bakalr CMS:
- Brand, Category, Product (core catalog)
- Review, Rating (customer feedback)
- Customer, Wishlist (customer management)
- Collection, Banner (merchandising)
- Coupon, ShippingZone (promotions & logistics)

Run with: docker-compose exec backend python scripts/create_boutique_content_types.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.db.session import SessionLocal
from backend.models.content import ContentType
from backend.models.organization import Organization
from backend.models.user import User


def create_boutique_content_types():
    """Create comprehensive e-commerce content types"""
    print("=" * 70)
    print("Creating Bakalr Boutique E-Commerce Content Types")
    print("=" * 70)

    db = SessionLocal()
    try:
        # Find user's organization
        user = db.query(User).filter(User.email == "bsakweson@gmail.com").first()
        if not user:
            print("❌ User not found. Please register first at http://localhost:3000")
            return

        org = db.query(Organization).filter(Organization.id == user.organization_id).first()
        if not org:
            print("❌ Organization not found")
            return

        print(f"🏢 Organization: {org.name}")
        print(f"👤 User: {user.email}\n")

        # Comprehensive e-commerce content types
        content_types = [
            # ==================== CORE CATALOG ====================
            {
                "name": "Brand",
                "api_id": "brand",
                "description": "E-commerce brand/manufacturer",
                "icon": "🏷️",
                "fields": [
                    {"name": "name", "type": "text", "label": "Brand Name", "required": True},
                    {"name": "slug", "type": "text", "label": "URL Slug", "required": True},
                    {"name": "description", "type": "richtext", "label": "Description", "required": False},
                    {"name": "logo_url", "type": "image", "label": "Logo", "required": False},
                    {"name": "banner_url", "type": "image", "label": "Banner Image", "required": False},
                    {"name": "website_url", "type": "url", "label": "Website URL", "required": False},
                    {"name": "is_active", "type": "boolean", "label": "Active", "required": False},
                    {"name": "featured", "type": "boolean", "label": "Featured Brand", "required": False},
                    {"name": "sort_order", "type": "number", "label": "Sort Order", "required": False},
                    {"name": "attributes", "type": "json", "label": "Additional Attributes", "required": False},
                    {"name": "meta_title", "type": "text", "label": "SEO Title", "required": False},
                    {"name": "meta_description", "type": "textarea", "label": "SEO Description", "required": False},
                ]
            },
            {
                "name": "Category",
                "api_id": "category",
                "description": "Product category hierarchy",
                "icon": "📂",
                "fields": [
                    {"name": "name", "type": "text", "label": "Category Name", "required": True},
                    {"name": "slug", "type": "text", "label": "URL Slug", "required": True},
                    {"name": "description", "type": "richtext", "label": "Description", "required": False},
                    {"name": "parent_id", "type": "text", "label": "Parent Category ID", "required": False},
                    {"name": "image_url", "type": "image", "label": "Category Image", "required": False},
                    {"name": "banner_url", "type": "image", "label": "Banner Image", "required": False},
                    {"name": "icon", "type": "text", "label": "Icon (emoji or class)", "required": False},
                    {"name": "is_active", "type": "boolean", "label": "Active", "required": False},
                    {"name": "featured", "type": "boolean", "label": "Featured Category", "required": False},
                    {"name": "sort_order", "type": "number", "label": "Sort Order", "required": False},
                    {"name": "product_count", "type": "number", "label": "Product Count", "required": False},
                    {"name": "meta_title", "type": "text", "label": "SEO Title", "required": False},
                    {"name": "meta_description", "type": "textarea", "label": "SEO Description", "required": False},
                ]
            },
            {
                "name": "Product",
                "api_id": "product",
                "description": "E-commerce product catalog",
                "icon": "🛍️",
                "fields": [
                    # Basic Info
                    {"name": "name", "type": "text", "label": "Product Name", "required": True},
                    {"name": "slug", "type": "text", "label": "URL Slug", "required": True},
                    {"name": "sku", "type": "text", "label": "SKU", "required": True},
                    {"name": "barcode", "type": "text", "label": "Barcode/UPC", "required": False},
                    
                    # Description
                    {"name": "description", "type": "richtext", "label": "Full Description", "required": True},
                    {"name": "short_description", "type": "textarea", "label": "Short Description", "required": False},
                    {"name": "highlights", "type": "json", "label": "Key Highlights (array)", "required": False},
                    
                    # Pricing
                    {"name": "price", "type": "number", "label": "Price", "required": True},
                    {"name": "compare_at_price", "type": "number", "label": "Compare at Price", "required": False},
                    {"name": "cost", "type": "number", "label": "Cost", "required": False},
                    {"name": "currency", "type": "text", "label": "Currency", "required": False},
                    {"name": "tax_code", "type": "text", "label": "Tax Code", "required": False},
                    
                    # Media
                    {"name": "images", "type": "json", "label": "Product Images (JSON array)", "required": False},
                    {"name": "featured_image", "type": "image", "label": "Featured Image", "required": False},
                    {"name": "video_url", "type": "url", "label": "Product Video URL", "required": False},
                    
                    # Classification
                    {"name": "brand_id", "type": "text", "label": "Brand ID", "required": False},
                    {"name": "category_id", "type": "text", "label": "Category ID", "required": False},
                    {"name": "tags", "type": "text", "label": "Tags (comma-separated)", "required": False},
                    {"name": "collections", "type": "json", "label": "Collection IDs (array)", "required": False},
                    
                    # Inventory
                    {"name": "in_stock", "type": "boolean", "label": "In Stock", "required": False},
                    {"name": "stock_quantity", "type": "number", "label": "Stock Quantity", "required": False},
                    {"name": "low_stock_threshold", "type": "number", "label": "Low Stock Alert", "required": False},
                    {"name": "track_inventory", "type": "boolean", "label": "Track Inventory", "required": False},
                    {"name": "allow_backorder", "type": "boolean", "label": "Allow Backorder", "required": False},
                    
                    # Shipping
                    {"name": "weight", "type": "number", "label": "Weight (kg)", "required": False},
                    {"name": "dimensions", "type": "json", "label": "Dimensions (L×W×H)", "required": False},
                    {"name": "requires_shipping", "type": "boolean", "label": "Requires Shipping", "required": False},
                    
                    # Variants & Options
                    {"name": "has_variants", "type": "boolean", "label": "Has Variants", "required": False},
                    {"name": "variants", "type": "json", "label": "Product Variants (JSON)", "required": False},
                    {"name": "options", "type": "json", "label": "Product Options (size, color, etc.)", "required": False},
                    
                    # Display & Marketing
                    {"name": "featured", "type": "boolean", "label": "Featured Product", "required": False},
                    {"name": "new_arrival", "type": "boolean", "label": "New Arrival", "required": False},
                    {"name": "best_seller", "type": "boolean", "label": "Best Seller", "required": False},
                    {"name": "on_sale", "type": "boolean", "label": "On Sale", "required": False},
                    {"name": "badge", "type": "text", "label": "Badge Text", "required": False},
                    {"name": "sort_order", "type": "number", "label": "Sort Order", "required": False},
                    
                    # Reviews & Ratings
                    {"name": "rating_average", "type": "number", "label": "Average Rating", "required": False},
                    {"name": "rating_count", "type": "number", "label": "Rating Count", "required": False},
                    {"name": "review_count", "type": "number", "label": "Review Count", "required": False},
                    
                    # Additional Data
                    {"name": "attributes", "type": "json", "label": "Product Attributes (JSON)", "required": False},
                    {"name": "related_products", "type": "json", "label": "Related Product IDs", "required": False},
                    
                    # SEO
                    {"name": "meta_title", "type": "text", "label": "SEO Title", "required": False},
                    {"name": "meta_description", "type": "textarea", "label": "SEO Description", "required": False},
                    {"name": "meta_keywords", "type": "text", "label": "SEO Keywords", "required": False},
                ]
            },
            
            # ==================== CUSTOMER FEEDBACK ====================
            {
                "name": "Review",
                "api_id": "review",
                "description": "Customer product reviews",
                "icon": "💬",
                "fields": [
                    {"name": "product_id", "type": "text", "label": "Product ID", "required": True},
                    {"name": "customer_id", "type": "text", "label": "Customer ID", "required": True},
                    {"name": "customer_name", "type": "text", "label": "Customer Name", "required": True},
                    {"name": "customer_email", "type": "email", "label": "Customer Email", "required": False},
                    {"name": "rating", "type": "number", "label": "Rating (1-5)", "required": True},
                    {"name": "title", "type": "text", "label": "Review Title", "required": True},
                    {"name": "content", "type": "richtext", "label": "Review Content", "required": True},
                    {"name": "images", "type": "json", "label": "Review Images", "required": False},
                    {"name": "verified_purchase", "type": "boolean", "label": "Verified Purchase", "required": False},
                    {"name": "helpful_count", "type": "number", "label": "Helpful Count", "required": False},
                    {"name": "unhelpful_count", "type": "number", "label": "Unhelpful Count", "required": False},
                    {"name": "is_approved", "type": "boolean", "label": "Approved", "required": False},
                    {"name": "reply", "type": "richtext", "label": "Store Reply", "required": False},
                    {"name": "reply_date", "type": "datetime", "label": "Reply Date", "required": False},
                ]
            },
            {
                "name": "Rating",
                "api_id": "rating",
                "description": "Quick product ratings",
                "icon": "⭐",
                "fields": [
                    {"name": "product_id", "type": "text", "label": "Product ID", "required": True},
                    {"name": "customer_id", "type": "text", "label": "Customer ID", "required": True},
                    {"name": "rating", "type": "number", "label": "Rating (1-5)", "required": True},
                    {"name": "dimensions", "type": "json", "label": "Rating Dimensions (quality, value, etc.)", "required": False},
                    {"name": "verified_purchase", "type": "boolean", "label": "Verified Purchase", "required": False},
                ]
            },
            
            # ==================== CUSTOMER MANAGEMENT ====================
            {
                "name": "Customer",
                "api_id": "customer",
                "description": "Customer profiles",
                "icon": "👤",
                "fields": [
                    {"name": "first_name", "type": "text", "label": "First Name", "required": True},
                    {"name": "last_name", "type": "text", "label": "Last Name", "required": True},
                    {"name": "email", "type": "email", "label": "Email", "required": True},
                    {"name": "phone", "type": "text", "label": "Phone", "required": False},
                    {"name": "avatar_url", "type": "image", "label": "Avatar", "required": False},
                    {"name": "addresses", "type": "json", "label": "Addresses (JSON array)", "required": False},
                    {"name": "default_address_id", "type": "text", "label": "Default Address ID", "required": False},
                    {"name": "tags", "type": "text", "label": "Customer Tags", "required": False},
                    {"name": "notes", "type": "textarea", "label": "Internal Notes", "required": False},
                    {"name": "total_spent", "type": "number", "label": "Total Spent", "required": False},
                    {"name": "order_count", "type": "number", "label": "Order Count", "required": False},
                    {"name": "accepts_marketing", "type": "boolean", "label": "Accepts Marketing", "required": False},
                    {"name": "is_active", "type": "boolean", "label": "Active", "required": False},
                ]
            },
            {
                "name": "Wishlist",
                "api_id": "wishlist",
                "description": "Customer wishlists",
                "icon": "❤️",
                "fields": [
                    {"name": "customer_id", "type": "text", "label": "Customer ID", "required": True},
                    {"name": "product_ids", "type": "json", "label": "Product IDs (array)", "required": True},
                    {"name": "name", "type": "text", "label": "Wishlist Name", "required": False},
                    {"name": "is_public", "type": "boolean", "label": "Public Wishlist", "required": False},
                    {"name": "share_token", "type": "text", "label": "Share Token", "required": False},
                ]
            },
            
            # ==================== MERCHANDISING ====================
            {
                "name": "Collection",
                "api_id": "collection",
                "description": "Product collections",
                "icon": "📦",
                "fields": [
                    {"name": "name", "type": "text", "label": "Collection Name", "required": True},
                    {"name": "slug", "type": "text", "label": "URL Slug", "required": True},
                    {"name": "description", "type": "richtext", "label": "Description", "required": False},
                    {"name": "image_url", "type": "image", "label": "Collection Image", "required": False},
                    {"name": "banner_url", "type": "image", "label": "Banner Image", "required": False},
                    {"name": "product_ids", "type": "json", "label": "Product IDs (array)", "required": False},
                    {"name": "rules", "type": "json", "label": "Auto-collection Rules", "required": False},
                    {"name": "is_automated", "type": "boolean", "label": "Automated Collection", "required": False},
                    {"name": "is_active", "type": "boolean", "label": "Active", "required": False},
                    {"name": "featured", "type": "boolean", "label": "Featured Collection", "required": False},
                    {"name": "sort_order", "type": "number", "label": "Sort Order", "required": False},
                    {"name": "meta_title", "type": "text", "label": "SEO Title", "required": False},
                    {"name": "meta_description", "type": "textarea", "label": "SEO Description", "required": False},
                ]
            },
            {
                "name": "Banner",
                "api_id": "banner",
                "description": "Homepage and promotional banners",
                "icon": "🎨",
                "fields": [
                    {"name": "title", "type": "text", "label": "Banner Title", "required": True},
                    {"name": "subtitle", "type": "text", "label": "Subtitle", "required": False},
                    {"name": "image_url", "type": "image", "label": "Banner Image", "required": True},
                    {"name": "mobile_image_url", "type": "image", "label": "Mobile Image", "required": False},
                    {"name": "link_url", "type": "url", "label": "Link URL", "required": False},
                    {"name": "button_text", "type": "text", "label": "Button Text", "required": False},
                    {"name": "position", "type": "text", "label": "Position (hero, sidebar, etc.)", "required": False},
                    {"name": "text_position", "type": "text", "label": "Text Position (left, center, right)", "required": False},
                    {"name": "text_color", "type": "text", "label": "Text Color", "required": False},
                    {"name": "overlay_opacity", "type": "number", "label": "Overlay Opacity (0-1)", "required": False},
                    {"name": "is_active", "type": "boolean", "label": "Active", "required": False},
                    {"name": "start_date", "type": "datetime", "label": "Start Date", "required": False},
                    {"name": "end_date", "type": "datetime", "label": "End Date", "required": False},
                    {"name": "sort_order", "type": "number", "label": "Sort Order", "required": False},
                ]
            },
            
            # ==================== PROMOTIONS & LOGISTICS ====================
            {
                "name": "Coupon",
                "api_id": "coupon",
                "description": "Discount coupons and promo codes",
                "icon": "🎫",
                "fields": [
                    {"name": "code", "type": "text", "label": "Coupon Code", "required": True},
                    {"name": "type", "type": "text", "label": "Type (percentage, fixed, free_shipping)", "required": True},
                    {"name": "value", "type": "number", "label": "Discount Value", "required": True},
                    {"name": "description", "type": "textarea", "label": "Description", "required": False},
                    {"name": "min_purchase", "type": "number", "label": "Minimum Purchase", "required": False},
                    {"name": "max_discount", "type": "number", "label": "Maximum Discount", "required": False},
                    {"name": "usage_limit", "type": "number", "label": "Usage Limit", "required": False},
                    {"name": "usage_count", "type": "number", "label": "Usage Count", "required": False},
                    {"name": "per_customer_limit", "type": "number", "label": "Per Customer Limit", "required": False},
                    {"name": "applicable_products", "type": "json", "label": "Applicable Product IDs", "required": False},
                    {"name": "applicable_categories", "type": "json", "label": "Applicable Category IDs", "required": False},
                    {"name": "excluded_products", "type": "json", "label": "Excluded Product IDs", "required": False},
                    {"name": "is_active", "type": "boolean", "label": "Active", "required": False},
                    {"name": "start_date", "type": "datetime", "label": "Start Date", "required": False},
                    {"name": "end_date", "type": "datetime", "label": "End Date", "required": False},
                ]
            },
            {
                "name": "ShippingZone",
                "api_id": "shipping_zone",
                "description": "Shipping zones and rates",
                "icon": "🚚",
                "fields": [
                    {"name": "name", "type": "text", "label": "Zone Name", "required": True},
                    {"name": "countries", "type": "json", "label": "Countries (array)", "required": True},
                    {"name": "regions", "type": "json", "label": "Regions/States (array)", "required": False},
                    {"name": "rates", "type": "json", "label": "Shipping Rates (JSON)", "required": True},
                    {"name": "free_shipping_threshold", "type": "number", "label": "Free Shipping Above", "required": False},
                    {"name": "is_active", "type": "boolean", "label": "Active", "required": False},
                    {"name": "sort_order", "type": "number", "label": "Sort Order", "required": False},
                ]
            }
        ]

        import json
        
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for ct_data in content_types:
            icon = ct_data.get("icon", "📦")
            
            # Check if content type already exists
            existing = db.query(ContentType).filter(
                ContentType.api_id == ct_data["api_id"],
                ContentType.organization_id == org.id
            ).first()

            if existing:
                # Delete and recreate to ensure schema is up to date
                print(f"🔄 Updating '{ct_data['name']}' (was ID: {existing.id})")
                db.delete(existing)
                db.commit()
                updated_count += 1

            # Create content type
            content_type = ContentType(
                organization_id=org.id,
                name=ct_data["name"],
                api_id=ct_data["api_id"],
                description=ct_data["description"],
                fields_schema=json.dumps(ct_data["fields"]),
                is_published=True
            )

            db.add(content_type)
            db.commit()
            db.refresh(content_type)

            action = "Updated" if existing else "Created"
            print(f"{icon} {action} '{ct_data['name']}' (ID: {content_type.id}, {len(ct_data['fields'])} fields)")
            created_count += 1

        print("\n" + "=" * 70)
        print(f"✅ Total Content Types: {created_count}")
        if updated_count > 0:
            print(f"🔄 Updated (recreated): {updated_count}")
        print("=" * 70)

        print("\n📊 Content Types Created:")
        print("  🏷️  Brand - Complete brand/manufacturer profiles")
        print("  📂 Category - Hierarchical product categories")
        print("  🛍️  Product - Full-featured product catalog")
        print("  💬 Review - Customer product reviews")
        print("  ⭐ Rating - Quick product ratings")
        print("  👤 Customer - Customer profiles & data")
        print("  ❤️  Wishlist - Customer wishlists")
        print("  📦 Collection - Curated product collections")
        print("  🎨 Banner - Promotional banners")
        print("  🎫 Coupon - Discount codes & promotions")
        print("  🚚 ShippingZone - Shipping zones & rates")

        print("\n📋 Next Steps:")
        print("1. Visit http://localhost:3000/dashboard/content-types to view all types")
        print("2. Create sample content entries (brands, categories, products)")
        print("3. Build BakalrCMSClient for bakalr-boutique integration")
        print("4. Test the full e-commerce workflow")
        print("\n💡 Pro Tip: You now have a world-class e-commerce content architecture!")

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_boutique_content_types()
