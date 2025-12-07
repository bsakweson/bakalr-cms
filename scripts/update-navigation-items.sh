#!/bin/bash

# Update Navigation content type to use nav_items array pattern
# This is the better, more flexible approach for navigation menus

API_URL="${CMS_API_URL:-http://localhost:8000}"
API_KEY="${CMS_API_KEY:-bk_p4mPH5PGxFb9yk3jd9O12ChtBcCt8fGfDlagg70tobI}"

echo "Updating Navigation to use items array pattern..."
echo "API URL: $API_URL"

# Get header navigation entry
echo ""
echo "=== Updating Header Navigation ==="
HEADER_NAV=$(curl -s "$API_URL/api/v1/content/entries?content_type_slug=navigation&slug=header-navigation" \
    -H "X-API-Key: $API_KEY")

HEADER_ID=$(echo "$HEADER_NAV" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data['items'][0]['id'] if data.get('items') else '')" 2>/dev/null)

if [ -z "$HEADER_ID" ]; then
    echo "Error: Could not find header navigation entry"
else
    echo "Header Navigation ID: $HEADER_ID"

    # Update with proper items array structure
    response=$(curl -s -w "\n%{http_code}" -X PATCH "$API_URL/api/v1/content/entries/$HEADER_ID" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d '{
            "data": {
                "menu_key": "header-navigation",
                "items": [
                    {"label": "Shop", "href": "/products", "icon": null},
                    {"label": "Categories", "href": "/categories", "icon": null},
                    {"label": "Brands", "href": "/brands", "icon": null},
                    {"label": "About", "href": "/about", "icon": null},
                    {"label": "Contact", "href": "/contact", "icon": null}
                ],
                "sign_in_text": "Sign In",
                "sign_up_text": "Sign Up",
                "search_placeholder": "Search products...",
                "view_cart_text": "View Cart"
            }
        }')

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ]; then
        echo "✓ Header navigation updated with items array"
    else
        echo "✗ Failed to update header navigation (HTTP $http_code)"
        echo "Response: $body"
    fi
fi

# Get mobile navigation entry
echo ""
echo "=== Updating Mobile Navigation ==="
MOBILE_ID=$(curl -s "$API_URL/api/v1/content/entries?content_type_slug=navigation&slug=mobile-navigation" \
    -H "X-API-Key: $API_KEY" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data['items'][0]['id'] if data.get('items') else '')" 2>/dev/null)

if [ -z "$MOBILE_ID" ]; then
    echo "Mobile navigation not found, skipping..."
else
    echo "Mobile Navigation ID: $MOBILE_ID"

    response=$(curl -s -w "\n%{http_code}" -X PATCH "$API_URL/api/v1/content/entries/$MOBILE_ID" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d '{
            "data": {
                "menu_key": "mobile-navigation",
                "items": [
                    {"label": "Home", "href": "/", "icon": "home"},
                    {"label": "Shop", "href": "/products", "icon": "shopping-bag"},
                    {"label": "Categories", "href": "/categories", "icon": "grid"},
                    {"label": "Brands", "href": "/brands", "icon": "tag"},
                    {"label": "About", "href": "/about", "icon": "info"},
                    {"label": "Contact", "href": "/contact", "icon": "mail"},
                    {"label": "My Account", "href": "/account", "icon": "user"},
                    {"label": "Cart", "href": "/cart", "icon": "shopping-cart"}
                ],
                "sign_in_text": "Sign In",
                "sign_up_text": "Sign Up",
                "search_placeholder": "Search...",
                "view_cart_text": "View Cart"
            }
        }')

    http_code=$(echo "$response" | tail -n1)

    if [ "$http_code" = "200" ]; then
        echo "✓ Mobile navigation updated with items array"
    else
        echo "✗ Failed to update mobile navigation (HTTP $http_code)"
    fi
fi

# Get footer navigation entry (if exists separately)
echo ""
echo "=== Checking Footer Navigation ==="
FOOTER_NAV_ID=$(curl -s "$API_URL/api/v1/content/entries?content_type_slug=navigation&slug=footer-navigation" \
    -H "X-API-Key: $API_KEY" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data['items'][0]['id'] if data.get('items') else '')" 2>/dev/null)

if [ -z "$FOOTER_NAV_ID" ]; then
    echo "Footer navigation not found (using Footer content type instead)"
else
    echo "Footer Navigation ID: $FOOTER_NAV_ID"

    response=$(curl -s -w "\n%{http_code}" -X PATCH "$API_URL/api/v1/content/entries/$FOOTER_NAV_ID" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d '{
            "data": {
                "menu_key": "footer-navigation",
                "items": [
                    {"label": "About Us", "href": "/about"},
                    {"label": "Contact", "href": "/contact"},
                    {"label": "Privacy Policy", "href": "/privacy"},
                    {"label": "Terms of Service", "href": "/terms"}
                ],
                "sign_in_text": null,
                "sign_up_text": null,
                "search_placeholder": null,
                "view_cart_text": null
            }
        }')

    http_code=$(echo "$response" | tail -n1)

    if [ "$http_code" = "200" ]; then
        echo "✓ Footer navigation updated"
    else
        echo "✗ Failed to update footer navigation (HTTP $http_code)"
    fi
fi

echo ""
echo "========================================"
echo "Navigation update complete!"
echo "========================================"
echo ""
echo "Navigation items array structure:"
echo '  { "label": "Shop", "href": "/products", "icon": "shopping-bag" }'
echo ""
echo "This pattern allows:"
echo "  - Dynamic menu items (add/remove without code changes)"
echo "  - Localized labels (translated per locale)"
echo "  - Optional icons per item"
echo "  - Nested menus (add children array if needed)"
