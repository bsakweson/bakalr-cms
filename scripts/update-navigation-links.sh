#!/bin/bash

# Update CMS navigation links to use correct routes
# Fixes footer and header navigation links

API_URL="${CMS_API_URL:-http://localhost:8000}"
API_KEY="${CMS_API_KEY:-bk_p4mPH5PGxFb9yk3jd9O12ChtBcCt8fGfDlagg70tobI}"

echo "Updating navigation links in CMS..."
echo "API URL: $API_URL"

# 1. Get footer entry ID
echo ""
echo "=== Updating Footer ==="
FOOTER_ID=$(curl -s "$API_URL/api/v1/content/entries?content_type_slug=footer&limit=1" \
    -H "X-API-Key: $API_KEY" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data['items'][0]['id'] if data.get('items') else '')" 2>/dev/null)

if [ -z "$FOOTER_ID" ]; then
    echo "Error: Could not find footer entry"
else
    echo "Footer ID: $FOOTER_ID"

    # Update footer with correct category links
    response=$(curl -s -w "\n%{http_code}" -X PATCH "$API_URL/api/v1/content/entries/$FOOTER_ID" \
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
                            {"label": "All Products", "href": "/products"},
                            {"label": "Brazilian Hair", "href": "/categories/brazilian-hair"},
                            {"label": "Wigs", "href": "/categories/wigs"},
                            {"label": "Closures", "href": "/categories/closures"},
                            {"label": "Brands", "href": "/brands"}
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

    if [ "$http_code" = "200" ]; then
        echo "✓ Footer updated successfully"
    else
        echo "✗ Failed to update footer (HTTP $http_code)"
        echo "Response: $(echo "$response" | sed '$d')"
    fi
fi

# 2. Get header navigation entry ID
echo ""
echo "=== Updating Header Navigation ==="
HEADER_ID=$(curl -s "$API_URL/api/v1/content/entries?content_type_slug=navigation&limit=1" \
    -H "X-API-Key: $API_KEY" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data['items'][0]['id'] if data.get('items') else '')" 2>/dev/null)

if [ -z "$HEADER_ID" ]; then
    echo "Error: Could not find header navigation entry"
else
    echo "Header ID: $HEADER_ID"

    # Update header navigation labels (structure uses individual link labels)
    response=$(curl -s -w "\n%{http_code}" -X PATCH "$API_URL/api/v1/content/entries/$HEADER_ID" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d '{
            "data": {
                "menu_key": "header-navigation",
                "items": [
                    {"label": "Shop", "href": "/products"},
                    {"label": "Categories", "href": "/categories"},
                    {"label": "Brands", "href": "/brands"},
                    {"label": "About", "href": "/about"},
                    {"label": "Contact", "href": "/contact"}
                ],
                "home_link": "Home",
                "products_link": "Products",
                "categories_link": "Categories",
                "brands_link": "Brands",
                "about_link": "About",
                "contact_link": "Contact",
                "cart_text": "Cart",
                "profile_text": "Profile",
                "logout_text": "Logout",
                "search_placeholder": "Search products...",
                "sign_in_text": "Sign In",
                "sign_up_text": "Sign Up",
                "view_cart_text": "View Cart"
            }
        }')

    http_code=$(echo "$response" | tail -n1)

    if [ "$http_code" = "200" ]; then
        echo "✓ Header navigation updated successfully"
    else
        echo "✗ Failed to update header navigation (HTTP $http_code)"
        echo "Response: $(echo "$response" | sed '$d')"
    fi
fi

echo ""
echo "========================================"
echo "Navigation update complete!"
echo "========================================"
echo ""
echo "Updated links:"
echo "  Footer: /categories/X instead of /category/X"
echo "  Header: /products, /categories, /brands, /about, /contact"
