#!/bin/bash

# Create Bakalr Boutique content types via API
# Usage: ./scripts/create_boutique_via_api.sh

set -e

API_URL="http://localhost:8000/api/v1"
EMAIL="bsakweson@gmail.com"
PASSWORD="Angelbenise123!@#"

echo "============================================================"
echo "Creating Bakalr Boutique Content Types via API"
echo "============================================================"
echo ""

# Login and get token
echo "🔐 Logging in..."
TOKEN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token')

if [ "$ACCESS_TOKEN" == "null" ] || [ -z "$ACCESS_TOKEN" ]; then
  echo "❌ Login failed. Please check credentials or register at http://localhost:3000"
  echo "Response: $TOKEN_RESPONSE"
  exit 1
fi

echo "✅ Logged in successfully"
echo ""

# Create Brand content type
echo "📦 Creating Brand content type..."
BRAND_RESPONSE=$(curl -s -X POST "$API_URL/content/types" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Brand",
    "api_id": "brand",
    "description": "E-commerce brand/manufacturer",
    "fields": [
      {"name": "name", "type": "text", "label": "Brand Name", "required": true},
      {"name": "slug", "type": "text", "label": "URL Slug", "required": true},
      {"name": "description", "type": "textarea", "label": "Description", "required": false},
      {"name": "logo_url", "type": "url", "label": "Logo URL", "required": false},
      {"name": "website_url", "type": "url", "label": "Website URL", "required": false},
      {"name": "is_active", "type": "boolean", "label": "Active", "required": false},
      {"name": "attributes", "type": "json", "label": "Additional Attributes", "required": false}
    ]
  }')

BRAND_ID=$(echo $BRAND_RESPONSE | jq -r '.id // empty')
if [ -n "$BRAND_ID" ]; then
  echo "✅ Created Brand content type (ID: $BRAND_ID)"
else
  echo "⚠️  Brand might already exist or error occurred"
  echo "   Response: $(echo $BRAND_RESPONSE | jq -r '.detail // .message // "Unknown"')"
fi
echo ""

# Create Category content type
echo "📂 Creating Category content type..."
CATEGORY_RESPONSE=$(curl -s -X POST "$API_URL/content/types" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Category",
    "api_id": "category",
    "description": "Product category",
    "fields": [
      {"name": "name", "type": "text", "label": "Category Name", "required": true},
      {"name": "slug", "type": "text", "label": "URL Slug", "required": true},
      {"name": "description", "type": "textarea", "label": "Description", "required": false},
      {"name": "parent_id", "type": "text", "label": "Parent Category ID", "required": false},
      {"name": "image_url", "type": "url", "label": "Category Image", "required": false},
      {"name": "is_active", "type": "boolean", "label": "Active", "required": false},
      {"name": "sort_order", "type": "number", "label": "Sort Order", "required": false},
      {"name": "meta_title", "type": "text", "label": "SEO Title", "required": false},
      {"name": "meta_description", "type": "textarea", "label": "SEO Description", "required": false}
    ]
  }')

CATEGORY_ID=$(echo $CATEGORY_RESPONSE | jq -r '.id // empty')
if [ -n "$CATEGORY_ID" ]; then
  echo "✅ Created Category content type (ID: $CATEGORY_ID)"
else
  echo "⚠️  Category might already exist or error occurred"
  echo "   Response: $(echo $CATEGORY_RESPONSE | jq -r '.detail // .message // "Unknown"')"
fi
echo ""

# Create Product content type
echo "🛍️  Creating Product content type..."
PRODUCT_RESPONSE=$(curl -s -X POST "$API_URL/content/types" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Product",
    "api_id": "product",
    "description": "E-commerce product",
    "fields": [
      {"name": "name", "type": "text", "label": "Product Name", "required": true},
      {"name": "slug", "type": "text", "label": "URL Slug", "required": true},
      {"name": "sku", "type": "text", "label": "SKU", "required": true},
      {"name": "description", "type": "richtext", "label": "Description", "required": true},
      {"name": "short_description", "type": "textarea", "label": "Short Description", "required": false},
      {"name": "price", "type": "number", "label": "Price", "required": true},
      {"name": "compare_at_price", "type": "number", "label": "Compare at Price", "required": false},
      {"name": "cost", "type": "number", "label": "Cost", "required": false},
      {"name": "images", "type": "json", "label": "Product Images (JSON array)", "required": false},
      {"name": "featured_image", "type": "image", "label": "Featured Image", "required": false},
      {"name": "brand_id", "type": "text", "label": "Brand ID", "required": false},
      {"name": "category_id", "type": "text", "label": "Category ID", "required": false},
      {"name": "tags", "type": "text", "label": "Tags (comma-separated)", "required": false},
      {"name": "in_stock", "type": "boolean", "label": "In Stock", "required": false},
      {"name": "stock_quantity", "type": "number", "label": "Stock Quantity", "required": false},
      {"name": "weight", "type": "number", "label": "Weight (kg)", "required": false},
      {"name": "attributes", "type": "json", "label": "Product Attributes (JSON)", "required": false},
      {"name": "meta_title", "type": "text", "label": "SEO Title", "required": false},
      {"name": "meta_description", "type": "textarea", "label": "SEO Description", "required": false}
    ]
  }')

PRODUCT_ID=$(echo $PRODUCT_RESPONSE | jq -r '.id // empty')
if [ -n "$PRODUCT_ID" ]; then
  echo "✅ Created Product content type (ID: $PRODUCT_ID)"
else
  echo "⚠️  Product might already exist or error occurred"
  echo "   Response: $(echo $PRODUCT_RESPONSE | jq -r '.detail // .message // "Unknown"')"
fi
echo ""

echo "============================================================"
echo "✅ Content types creation complete!"
echo "============================================================"
echo ""
echo "📋 Next steps:"
echo "1. Visit http://localhost:3000/dashboard/content-types to view"
echo "2. Create sample content entries (brands, categories, products)"
echo "3. Build BakalrCMSClient for bakalr-boutique integration"
echo ""
