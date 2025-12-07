#!/bin/bash

# Update footer links to use correct category paths
# Also creates a shop redirect page

API_URL="${CMS_API_URL:-http://localhost:8000}"
API_KEY="${CMS_API_KEY:-bk_p4mPH5PGxFb9yk3jd9O12ChtBcCt8fGfDlagg70tobI}"

echo "Updating footer links in CMS..."
echo "API URL: $API_URL"

# Get footer entry ID
FOOTER_ID=$(curl -s "$API_URL/api/v1/content/entries?content_type_slug=footer&limit=1" \
    -H "X-API-Key: $API_KEY" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data['items'][0]['id'] if data.get('items') else '')" 2>/dev/null)

if [ -z "$FOOTER_ID" ]; then
    echo "Error: Could not find footer entry"
    exit 1
fi

echo "Footer ID: $FOOTER_ID"

# Update footer with corrected links
echo ""
echo "Updating footer columns with correct category links..."

response=$(curl -s -w "\n%{http_code}" -X PUT "$API_URL/api/v1/content/entries/$FOOTER_ID" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -d '{
        "data": {
            "about_text": "Bakalr Boutique is your destination for premium beauty supplies. We carry the best brands in hair care, skincare, cosmetics, and more.",
            "copyright_text": "© 2025 Bakalr Boutique. All rights reserved.",
            "columns": [
                {
                    "title": "Shop",
                    "links": [
                        {"label": "All Products", "href": "/shop"},
                        {"label": "Wigs", "href": "/categories/wigs"},
                        {"label": "Brazilian Hair", "href": "/categories/brazilian-hair"},
                        {"label": "Hair Tools", "href": "/categories/hair-tools"},
                        {"label": "Treatments & Oils", "href": "/categories/treatments-oils"}
                    ]
                },
                {
                    "title": "Customer Service",
                    "links": [
                        {"label": "Contact Us", "href": "/contact"},
                        {"label": "FAQ", "href": "/faq"},
                        {"label": "Shipping Info", "href": "/shipping"},
                        {"label": "Returns", "href": "/returns"},
                        {"label": "Track Order", "href": "/account/orders"}
                    ]
                },
                {
                    "title": "Company",
                    "links": [
                        {"label": "About Us", "href": "/about"},
                        {"label": "Careers", "href": "/careers"},
                        {"label": "Press", "href": "/press"},
                        {"label": "Privacy Policy", "href": "/privacy"},
                        {"label": "Terms of Service", "href": "/terms"}
                    ]
                }
            ],
            "social_links": {
                "facebook": "https://facebook.com/bakalrboutique",
                "instagram": "https://instagram.com/bakalrboutique",
                "twitter": "https://twitter.com/bakalrboutique",
                "youtube": "https://youtube.com/@bakalrboutique",
                "tiktok": "https://tiktok.com/@bakalrboutique"
            },
            "payment_icons": ["visa", "mastercard", "amex", "discover", "paypal", "apple-pay", "google-pay"]
        }
    }')

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo "✓ Footer updated successfully"
else
    echo "✗ Failed to update footer (HTTP $http_code)"
    echo "Response: $body"
fi

echo ""
echo "========================================"
echo "Footer update complete!"
echo "========================================"
