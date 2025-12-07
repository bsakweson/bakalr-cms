#!/bin/bash

# Update header navigation links to use correct category paths

API_URL="${CMS_API_URL:-http://localhost:8000}"
API_KEY="${CMS_API_KEY:-bk_p4mPH5PGxFb9yk3jd9O12ChtBcCt8fGfDlagg70tobI}"

echo "Updating header navigation in CMS..."
echo "API URL: $API_URL"

# Get header navigation entry ID (slug: header)
NAV_ID=$(curl -s "$API_URL/api/v1/content/entries?content_type_slug=navigation&slug=header" \
    -H "X-API-Key: $API_KEY" | python3 -c "import sys, json; data = json.load(sys.stdin); items = [i for i in data.get('items', []) if i.get('slug') == 'header']; print(items[0]['id'] if items else '')" 2>/dev/null)

if [ -z "$NAV_ID" ]; then
    echo "Error: Could not find header navigation entry"
    exit 1
fi

echo "Header Navigation ID: $NAV_ID"

# Update navigation with corrected links
echo ""
echo "Updating header navigation with correct category links..."

response=$(curl -s -w "\n%{http_code}" -X PUT "$API_URL/api/v1/content/entries/$NAV_ID" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -d '{
        "data": {
            "menu_key": "header",
            "items": [
                {
                    "href": "/",
                    "label": "Home",
                    "order": 1
                },
                {
                    "href": "/shop",
                    "label": "Shop",
                    "order": 2,
                    "children": [
                        {"href": "/categories/wigs", "label": "Wigs"},
                        {"href": "/categories/brazilian-hair", "label": "Brazilian Hair"},
                        {"href": "/categories/indian-hair", "label": "Indian Hair"},
                        {"href": "/categories/closures", "label": "Closures"},
                        {"href": "/categories/treatments-oils", "label": "Treatments & Oils"},
                        {"href": "/categories/hair-tools", "label": "Hair Tools"},
                        {"href": "/shop", "label": "Shop All"}
                    ]
                },
                {
                    "href": "/brands",
                    "label": "Brands",
                    "order": 3
                },
                {
                    "href": "/products?filter=new",
                    "label": "New Arrivals",
                    "order": 4
                },
                {
                    "href": "/products?filter=sale",
                    "label": "Sale",
                    "order": 5
                },
                {
                    "href": "/about",
                    "label": "About",
                    "order": 6
                },
                {
                    "href": "/contact",
                    "label": "Contact",
                    "order": 7
                }
            ],
            "sign_in_text": "Sign In",
            "sign_up_text": "Sign Up",
            "view_cart_text": "View Cart",
            "search_placeholder": "Search products..."
        }
    }')

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo "✓ Header navigation updated successfully"
else
    echo "✗ Failed to update header navigation (HTTP $http_code)"
    echo "Response: $body"
fi

echo ""
echo "========================================"
echo "Navigation update complete!"
echo "========================================"
