#!/bin/bash

# Create missing CMS page entries for bakalr-boutique
# Pages needed: shipping, returns, careers, press

API_URL="${CMS_API_URL:-http://localhost:8000}"
API_KEY="${CMS_API_KEY:-bk_p4mPH5PGxFb9yk3jd9O12ChtBcCt8fGfDlagg70tobI}"

# Content type ID for "page" - get dynamically
CONTENT_TYPE_ID=$(curl -s "$API_URL/api/v1/content/types" \
    -H "X-API-Key: $API_KEY" | python3 -c "import sys, json; data = json.load(sys.stdin); print(next((ct['id'] for ct in data if ct.get('api_id') == 'page'), ''))" 2>/dev/null)

if [ -z "$CONTENT_TYPE_ID" ]; then
    echo "Error: Could not find content type ID for 'page'"
    exit 1
fi

echo "Creating missing page entries in CMS..."
echo "API URL: $API_URL"
echo "Page Content Type ID: $CONTENT_TYPE_ID"

# Function to create a page
create_page() {
    local slug=$1
    local page_key=$2
    local seo_title=$3
    local seo_description=$4
    local sections=$5

    echo ""
    echo "Creating page: $slug"

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/api/v1/content/entries" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d "{
            \"content_type_id\": \"$CONTENT_TYPE_ID\",
            \"slug\": \"$slug\",
            \"status\": \"published\",
            \"seo_title\": \"$seo_title\",
            \"seo_description\": \"$seo_description\",
            \"data\": {
                \"page_key\": \"$page_key\",
                \"template\": \"landing\",
                \"sections\": $sections
            }
        }")

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "201" ] || [ "$http_code" = "200" ]; then
        echo "✓ Created page: $slug"
    elif [ "$http_code" = "400" ]; then
        echo "⚠ Page may already exist: $slug"
        echo "  Response: $body"
    else
        echo "✗ Failed to create page: $slug (HTTP $http_code)"
        echo "  Response: $body"
    fi
}

# 1. Shipping page
create_page "shipping" \
    "shipping" \
    "Shipping Information | Bakalr Boutique" \
    "Learn about our shipping options, delivery times, and shipping costs." \
    '[
        {
            "type": "page_header",
            "heading": "Shipping Information",
            "subheading": "Fast & Reliable Delivery"
        },
        {
            "type": "rich_text",
            "content": "<p>We offer multiple shipping options to get your beauty products to you as quickly as possible.</p><h3>Standard Shipping</h3><p>Free on orders over $50. Delivery in 5-7 business days.</p><h3>Express Shipping</h3><p>$9.99 flat rate. Delivery in 2-3 business days.</p><h3>Next Day Delivery</h3><p>$19.99 flat rate. Order by 2pm for next day delivery.</p>"
        },
        {
            "type": "rich_text",
            "content": "<h3>International Shipping</h3><p>We ship to over 50 countries worldwide. International shipping rates are calculated at checkout based on your location and order weight.</p><p>Please note that international orders may be subject to customs duties and taxes, which are the responsibility of the recipient.</p>"
        },
        {
            "type": "rich_text",
            "content": "<h3>Order Tracking</h3><p>Once your order ships, you will receive a confirmation email with a tracking number. You can track your order status in your account dashboard or using the link provided in the email.</p>"
        }
    ]'

# 2. Returns page
create_page "returns" \
    "returns" \
    "Returns & Exchanges | Bakalr Boutique" \
    "Our hassle-free return policy. Learn how to return or exchange your products." \
    '[
        {
            "type": "page_header",
            "heading": "Returns & Exchanges",
            "subheading": "Hassle-Free Returns"
        },
        {
            "type": "rich_text",
            "content": "<p>We want you to love your purchase. If you are not completely satisfied, we are here to help.</p><h3>Return Policy</h3><p>We accept returns within 30 days of purchase for most items in their original, unopened condition.</p><h4>Eligible Items</h4><ul><li>Unopened and unused products</li><li>Products in original packaging</li><li>Items with tags attached</li></ul><h4>Non-Returnable Items</h4><ul><li>Opened beauty products (for hygiene reasons)</li><li>Sale items marked as final sale</li><li>Gift cards</li></ul>"
        },
        {
            "type": "rich_text",
            "content": "<h3>How to Return</h3><ol><li>Log into your account and go to Order History</li><li>Select the order and items you wish to return</li><li>Print the prepaid return label</li><li>Pack items securely and drop off at any shipping location</li></ol><p>Refunds are processed within 5-7 business days of receiving your return.</p>"
        },
        {
            "type": "rich_text",
            "content": "<h3>Exchanges</h3><p>Need a different shade or size? We are happy to exchange your item. Follow the same return process and select Exchange as your reason. We will ship your new item as soon as we receive your return.</p>"
        }
    ]'

# 3. Careers page
create_page "careers" \
    "careers" \
    "Careers at Bakalr Boutique | Join Our Team" \
    "Join our passionate team at Bakalr Boutique. Explore career opportunities in beauty retail." \
    '[
        {
            "type": "page_header",
            "heading": "Join Our Team",
            "subheading": "Build Your Career in Beauty"
        },
        {
            "type": "rich_text",
            "content": "<p>At Bakalr Boutique, we are passionate about beauty and empowering our team members to grow.</p><h3>Why Work With Us</h3><p>We believe in creating an inclusive, supportive environment where creativity thrives.</p><h4>Benefits</h4><ul><li>Competitive salary and commission</li><li>Employee discount on all products</li><li>Health and wellness benefits</li><li>Professional development opportunities</li><li>Flexible scheduling</li></ul>"
        },
        {
            "type": "rich_text",
            "content": "<h3>Open Positions</h3><p>We are always looking for talented individuals to join our team. Current openings include:</p><ul><li><strong>Beauty Advisor</strong> - In-store customer service</li><li><strong>E-commerce Specialist</strong> - Digital marketing and sales</li><li><strong>Warehouse Associate</strong> - Fulfillment and logistics</li><li><strong>Customer Service Representative</strong> - Support team</li></ul>"
        },
        {
            "type": "cta",
            "heading": "Ready to Apply?",
            "description": "Send your resume to careers@bakalrboutique.com",
            "button_text": "Email Us",
            "button_url": "mailto:careers@bakalrboutique.com"
        }
    ]'

# 4. Press page
create_page "press" \
    "press" \
    "Press & Media | Bakalr Boutique" \
    "Press releases, media resources, and news about Bakalr Boutique." \
    '[
        {
            "type": "page_header",
            "heading": "Press & Media",
            "subheading": "Bakalr Boutique in the News"
        },
        {
            "type": "rich_text",
            "content": "<p>Find the latest news, press releases, and media resources about Bakalr Boutique.</p><h3>About Bakalr Boutique</h3><p>Bakalr Boutique is a premium beauty destination offering curated hair care, skincare, and cosmetics products. Founded with a mission to make professional-quality beauty accessible to everyone.</p><p>Our carefully selected product range features both established brands and emerging indie labels, with a focus on clean, effective formulations.</p>"
        },
        {
            "type": "rich_text",
            "content": "<h3>Press Releases</h3><h4>2025</h4><ul><li><strong>December 2025</strong> - Bakalr Boutique Launches New Website</li><li><strong>November 2025</strong> - Holiday Collection Announcement</li></ul>"
        },
        {
            "type": "rich_text",
            "content": "<h3>Media Resources</h3><p>For logo files, brand guidelines, and high-resolution images, please contact our press team.</p><h4>Press Contact</h4><p>Email: press@bakalrboutique.com</p>"
        }
    ]'

echo ""
echo "========================================"
echo "Page creation complete!"
echo "========================================"
