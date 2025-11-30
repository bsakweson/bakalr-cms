#!/bin/bash

# Run inside Docker container to create e-commerce content types
docker-compose exec -T backend python << 'PYTHON_SCRIPT'
import json
from backend.db.session import SessionLocal
from backend.models.content import ContentType
from backend.models.organization import Organization
from backend.models.user import User

db = SessionLocal()
try:
    user = db.query(User).filter(User.email == "bsakweson@gmail.com").first()
    org = db.query(Organization).filter(Organization.id == user.organization_id).first()
    
    print("=" * 70)
    print("Creating E-Commerce Content Types")
    print("=" * 70)
    print(f"🏢 {org.name}\n")
    
    content_types = [
        {
            "name": "Brand", "api_id": "brand", "icon": "🏷️",
            "description": "E-commerce brand/manufacturer",
            "fields": [
                {"name": "name", "type": "text", "label": "Brand Name", "required": True},
                {"name": "slug", "type": "text", "label": "URL Slug", "required": True},
                {"name": "description", "type": "richtext", "label": "Description"},
                {"name": "logo_url", "type": "image", "label": "Logo"},
                {"name": "banner_url", "type": "image", "label": "Banner Image"},
                {"name": "website_url", "type": "url", "label": "Website URL"},
                {"name": "is_active", "type": "boolean", "label": "Active"},
                {"name": "featured", "type": "boolean", "label": "Featured Brand"},
                {"name": "attributes", "type": "json", "label": "Attributes"},
            ]
        },
        {
            "name": "Category", "api_id": "category", "icon": "📂",
            "description": "Product category hierarchy",
            "fields": [
                {"name": "name", "type": "text", "label": "Name", "required": True},
                {"name": "slug", "type": "text", "label": "Slug", "required": True},
                {"name": "description", "type": "richtext", "label": "Description"},
                {"name": "parent_id", "type": "text", "label": "Parent ID"},
                {"name": "image_url", "type": "image", "label": "Image"},
                {"name": "is_active", "type": "boolean", "label": "Active"},
                {"name": "featured", "type": "boolean", "label": "Featured"},
            ]
        },
        {
            "name": "Product", "api_id": "product", "icon": "🛍️",
            "description": "E-commerce product catalog",
            "fields": [
                {"name": "name", "type": "text", "label": "Name", "required": True},
                {"name": "slug", "type": "text", "label": "Slug", "required": True},
                {"name": "sku", "type": "text", "label": "SKU", "required": True},
                {"name": "description", "type": "richtext", "label": "Description", "required": True},
                {"name": "price", "type": "number", "label": "Price", "required": True},
                {"name": "compare_at_price", "type": "number", "label": "Compare Price"},
                {"name": "images", "type": "json", "label": "Images (JSON)"},
                {"name": "featured_image", "type": "image", "label": "Featured Image"},
                {"name": "brand_id", "type": "text", "label": "Brand ID"},
                {"name": "category_id", "type": "text", "label": "Category ID"},
                {"name": "in_stock", "type": "boolean", "label": "In Stock"},
                {"name": "stock_quantity", "type": "number", "label": "Stock"},
                {"name": "featured", "type": "boolean", "label": "Featured"},
                {"name": "rating_average", "type": "number", "label": "Rating"},
            ]
        },
        {
            "name": "Review", "api_id": "review", "icon": "💬",
            "description": "Customer product reviews",
            "fields": [
                {"name": "product_id", "type": "text", "label": "Product ID", "required": True},
                {"name": "customer_name", "type": "text", "label": "Name", "required": True},
                {"name": "rating", "type": "number", "label": "Rating (1-5)", "required": True},
                {"name": "title", "type": "text", "label": "Title", "required": True},
                {"name": "content", "type": "richtext", "label": "Review", "required": True},
                {"name": "verified_purchase", "type": "boolean", "label": "Verified"},
                {"name": "is_approved", "type": "boolean", "label": "Approved"},
            ]
        },
        {
            "name": "Rating", "api_id": "rating", "icon": "⭐",
            "description": "Quick product ratings",
            "fields": [
                {"name": "product_id", "type": "text", "label": "Product ID", "required": True},
                {"name": "customer_id", "type": "text", "label": "Customer ID", "required": True},
                {"name": "rating", "type": "number", "label": "Rating (1-5)", "required": True},
                {"name": "verified_purchase", "type": "boolean", "label": "Verified"},
            ]
        },
        {
            "name": "Collection", "api_id": "collection", "icon": "📦",
            "description": "Product collections",
            "fields": [
                {"name": "name", "type": "text", "label": "Name", "required": True},
                {"name": "slug", "type": "text", "label": "Slug", "required": True},
                {"name": "description", "type": "richtext", "label": "Description"},
                {"name": "image_url", "type": "image", "label": "Image"},
                {"name": "product_ids", "type": "json", "label": "Product IDs"},
                {"name": "is_active", "type": "boolean", "label": "Active"},
                {"name": "featured", "type": "boolean", "label": "Featured"},
            ]
        },
        {
            "name": "Banner", "api_id": "banner", "icon": "🎨",
            "description": "Promotional banners",
            "fields": [
                {"name": "title", "type": "text", "label": "Title", "required": True},
                {"name": "image_url", "type": "image", "label": "Image", "required": True},
                {"name": "link_url", "type": "url", "label": "Link"},
                {"name": "button_text", "type": "text", "label": "Button Text"},
                {"name": "is_active", "type": "boolean", "label": "Active"},
                {"name": "sort_order", "type": "number", "label": "Order"},
            ]
        },
        {
            "name": "Coupon", "api_id": "coupon", "icon": "🎫",
            "description": "Discount coupons",
            "fields": [
                {"name": "code", "type": "text", "label": "Code", "required": True},
                {"name": "type", "type": "text", "label": "Type", "required": True},
                {"name": "value", "type": "number", "label": "Value", "required": True},
                {"name": "min_purchase", "type": "number", "label": "Min Purchase"},
                {"name": "usage_limit", "type": "number", "label": "Usage Limit"},
                {"name": "is_active", "type": "boolean", "label": "Active"},
            ]
        }
    ]
    
    for ct_data in content_types:
        existing = db.query(ContentType).filter(
            ContentType.api_id == ct_data["api_id"],
            ContentType.organization_id == org.id
        ).first()
        
        if existing:
            db.delete(existing)
            db.commit()
        
        ct = ContentType(
            organization_id=org.id,
            name=ct_data["name"],
            api_id=ct_data["api_id"],
            description=ct_data["description"],
            fields_schema=json.dumps(ct_data["fields"]),
            is_published=True
        )
        
        db.add(ct)
        db.commit()
        db.refresh(ct)
        
        print(f"{ct_data['icon']} Created {ct_data['name']} ({len(ct_data['fields'])} fields)")
    
    print("\n" + "=" * 70)
    print(f"✅ Created {len(content_types)} content types!")
    print("=" * 70)
    
finally:
    db.close()
PYTHON_SCRIPT
