#!/bin/bash

# Fix and update all navigation entries to use proper items array pattern
# Updates: header, header-navigation, mobile, footer navigation entries

API_URL="${CMS_API_URL:-http://localhost:8000}"
API_KEY="${CMS_API_KEY:-bk_p4mPH5PGxFb9yk3jd9O12ChtBcCt8fGfDlagg70tobI}"

echo "Fixing navigation entries in CMS..."
echo "API URL: $API_URL"

# Function to update a navigation entry
update_nav() {
    local entry_id=$1
    local name=$2
    local data=$3

    response=$(curl -s -w "\n%{http_code}" -X PATCH "$API_URL/api/v1/content/entries/$entry_id" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d "$data")

    http_code=$(echo "$response" | tail -n1)

    if [ "$http_code" = "200" ]; then
        echo "✓ $name updated"
    else
        echo "✗ Failed to update $name (HTTP $http_code)"
        echo "Response: $(echo "$response" | sed '$d')"
    fi
}

# 1. Fix header-navigation entry (was corrupted)
echo ""
echo "=== Fixing header-navigation ==="
HEADER_NAV_ID="a5f01393-6f22-440f-b066-6652d850ed93"
update_nav "$HEADER_NAV_ID" "header-navigation" '{
    "data": {
        "menu_key": "header-navigation",
        "items": [
            {"label": "Shop", "href": "/products"},
            {"label": "Categories", "href": "/categories"},
            {"label": "Brands", "href": "/brands"},
            {"label": "About", "href": "/about"},
            {"label": "Contact", "href": "/contact"}
        ],
        "sign_in_text": "Sign In",
        "sign_up_text": "Sign Up",
        "search_placeholder": "Search products...",
        "view_cart_text": "View Cart"
    }
}'

# 2. Update main header entry with dropdown menu
echo ""
echo "=== Updating header (with dropdown) ==="
HEADER_ID="a573e642-9894-42ee-895f-c833da7c39aa"
update_nav "$HEADER_ID" "header" '{
    "data": {
        "menu_key": "header",
        "items": [
            {"href": "/", "label": "Home", "order": 1},
            {
                "href": "/products",
                "label": "Shop",
                "order": 2,
                "children": [
                    {"href": "/categories/wigs", "label": "Wigs"},
                    {"href": "/categories/brazilian-hair", "label": "Brazilian Hair"},
                    {"href": "/categories/indian-hair", "label": "Indian Hair"},
                    {"href": "/categories/closures", "label": "Closures"},
                    {"href": "/categories/treatments-oils", "label": "Treatments & Oils"},
                    {"href": "/categories/hair-tools", "label": "Hair Tools"},
                    {"href": "/products", "label": "Shop All"}
                ]
            },
            {"href": "/brands", "label": "Brands", "order": 3},
            {"href": "/products?filter=new", "label": "New Arrivals", "order": 4},
            {"href": "/products?filter=sale", "label": "Sale", "order": 5},
            {"href": "/about", "label": "About", "order": 6},
            {"href": "/contact", "label": "Contact", "order": 7}
        ],
        "sign_in_text": "Sign In",
        "sign_up_text": "Sign Up",
        "view_cart_text": "View Cart",
        "search_placeholder": "Search products..."
    }
}'

# 3. Update mobile navigation
echo ""
echo "=== Updating mobile navigation ==="
MOBILE_ID="42f2d5c5-d72e-4ba9-a8b3-c694b8cc7fa9"
update_nav "$MOBILE_ID" "mobile" '{
    "data": {
        "menu_key": "mobile",
        "items": [
            {"label": "Home", "href": "/", "icon": "home", "order": 1},
            {"label": "Shop", "href": "/products", "icon": "shopping-bag", "order": 2},
            {"label": "Categories", "href": "/categories", "icon": "grid", "order": 3},
            {"label": "Brands", "href": "/brands", "icon": "tag", "order": 4},
            {"label": "Search", "href": "/search", "icon": "search", "order": 5},
            {"label": "Account", "href": "/account", "icon": "user", "order": 6},
            {"label": "Cart", "href": "/cart", "icon": "shopping-cart", "order": 7}
        ],
        "sign_in_text": "Sign In",
        "sign_up_text": "Sign Up",
        "search_placeholder": "Search...",
        "view_cart_text": "View Cart"
    }
}'

# 4. Update footer navigation
echo ""
echo "=== Updating footer navigation ==="
FOOTER_NAV_ID="4e6cf418-0657-4db5-a4c3-7ae6b2607002"
update_nav "$FOOTER_NAV_ID" "footer" '{
    "data": {
        "menu_key": "footer",
        "items": [
            {"label": "Shop", "href": "/products", "order": 1},
            {"label": "About Us", "href": "/about", "order": 2},
            {"label": "Contact", "href": "/contact", "order": 3},
            {"label": "FAQ", "href": "/faq", "order": 4},
            {"label": "Shipping", "href": "/shipping", "order": 5},
            {"label": "Returns", "href": "/returns", "order": 6},
            {"label": "Privacy Policy", "href": "/privacy", "order": 7},
            {"label": "Terms of Service", "href": "/terms", "order": 8}
        ]
    }
}'

echo ""
echo "========================================"
echo "Navigation fix complete!"
echo "========================================"
echo ""
echo "All navigation entries now use items array pattern:"
echo "  [{ label, href, icon?, order?, children? }]"
echo ""
echo "Routes updated from /shop to /products"
