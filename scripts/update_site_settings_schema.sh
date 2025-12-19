#!/bin/bash

# Update Site Settings Schema
# This script adds new fields to the site_settings content type in Bakalr CMS
# Fields added: payment_methods, timezones, date_formats, shipping_settings, notification_settings, store_settings

set -e

CMS_URL="${CMS_URL:-http://localhost:8000}"
EMAIL="${CMS_EMAIL:-bsakweson@gmail.com}"
PASSWORD="${CMS_PASSWORD:-Angelbenise1}"

echo "🔐 Logging into CMS..."
TOKEN=$(curl -s -X POST "${CMS_URL}/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}" | jq -r '.access_token')

if [ "$TOKEN" == "null" ] || [ -z "$TOKEN" ]; then
  echo "❌ Failed to authenticate"
  exit 1
fi

echo "✅ Authenticated successfully"

# Get site_settings content type ID
echo "🔍 Finding site_settings content type..."
CONTENT_TYPE_ID=$(curl -s "${CMS_URL}/api/v1/content/types" \
  -H "Authorization: Bearer ${TOKEN}" | jq -r '.[] | select(.api_id == "site_settings") | .id')

if [ -z "$CONTENT_TYPE_ID" ] || [ "$CONTENT_TYPE_ID" == "null" ]; then
  echo "❌ Could not find site_settings content type"
  exit 1
fi

echo "✅ Found site_settings content type (ID: ${CONTENT_TYPE_ID})"

# Get current fields
echo "📋 Getting current fields..."
CURRENT_FIELDS=$(curl -s "${CMS_URL}/api/v1/content/types/${CONTENT_TYPE_ID}" \
  -H "Authorization: Bearer ${TOKEN}" | jq '.fields')

echo "Current fields:"
echo "$CURRENT_FIELDS" | jq 'keys'

# Define new fields to add (as array format)
NEW_FIELDS='[
  {
    "name": "payment_methods",
    "type": "json",
    "required": false,
    "unique": false,
    "localized": false,
    "default": null,
    "validation": null,
    "help_text": "Available payment methods configuration"
  },
  {
    "name": "timezones",
    "type": "json",
    "required": false,
    "unique": false,
    "localized": false,
    "default": null,
    "validation": null,
    "help_text": "Available timezone options"
  },
  {
    "name": "date_formats",
    "type": "json",
    "required": false,
    "unique": false,
    "localized": false,
    "default": null,
    "validation": null,
    "help_text": "Available date format options"
  },
  {
    "name": "shipping_settings",
    "type": "json",
    "required": false,
    "unique": false,
    "localized": false,
    "default": null,
    "validation": null,
    "help_text": "Default shipping configuration"
  },
  {
    "name": "notification_settings",
    "type": "json",
    "required": false,
    "unique": false,
    "localized": false,
    "default": null,
    "validation": null,
    "help_text": "Default notification preferences"
  },
  {
    "name": "store_settings",
    "type": "json",
    "required": false,
    "unique": false,
    "localized": false,
    "default": null,
    "validation": null,
    "help_text": "Default store configuration options"
  }
]'

# Merge current fields with new fields (array concatenation)
echo "🔧 Merging fields..."
MERGED_FIELDS=$(echo "$CURRENT_FIELDS" | jq --argjson new "$NEW_FIELDS" '. + $new')

# Update content type
echo "📤 Updating content type..."
UPDATE_RESPONSE=$(curl -s -X PATCH "${CMS_URL}/api/v1/content/types/${CONTENT_TYPE_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{\"fields\": ${MERGED_FIELDS}}")

if echo "$UPDATE_RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
  echo "✅ Content type updated successfully!"
  echo "New fields:"
  echo "$UPDATE_RESPONSE" | jq '.fields | keys'
else
  echo "❌ Failed to update content type:"
  echo "$UPDATE_RESPONSE" | jq .
  exit 1
fi

# Now update the site_settings entry with sample data
echo ""
echo "🔍 Finding site_settings entry..."
ENTRY_ID=$(curl -s "${CMS_URL}/api/v1/content/entries?content_type_id=${CONTENT_TYPE_ID}&limit=1" \
  -H "Authorization: Bearer ${TOKEN}" | jq -r '.items[0].id')

if [ -z "$ENTRY_ID" ] || [ "$ENTRY_ID" == "null" ]; then
  echo "⚠️  No site_settings entry found. Skipping data update."
  exit 0
fi

echo "✅ Found site_settings entry (ID: ${ENTRY_ID})"

# Sample payment methods data
PAYMENT_METHODS='[
  {"id": "stripe", "name": "Stripe", "description": "Accept credit cards, Apple Pay, Google Pay and more", "icon": "S", "color": "#635BFF", "category": "card", "enabled": true, "regions": []},
  {"id": "paypal", "name": "PayPal", "description": "Accept PayPal payments worldwide", "icon": "PP", "color": "#003087", "category": "wallet", "enabled": true, "regions": []},
  {"id": "cod", "name": "Cash on Delivery", "description": "Customers pay when package arrives", "icon": "💵", "color": "#27AE60", "category": "cash", "enabled": true, "regions": []},
  {"id": "mpesa", "name": "M-Pesa", "description": "Mobile money payments (Kenya, Tanzania, DRC, etc.)", "icon": "M", "color": "#4BA228", "category": "mobile", "enabled": false, "regions": ["KE", "TZ", "CD", "GH", "MZ", "EG"]},
  {"id": "mtn_momo", "name": "MTN Mobile Money", "description": "MTN MoMo payments (Ghana, Uganda, Rwanda, etc.)", "icon": "MTN", "color": "#FFCB05", "category": "mobile", "enabled": false, "regions": ["GH", "UG", "RW", "BJ", "CI", "CM", "CG"]},
  {"id": "airtel_money", "name": "Airtel Money", "description": "Airtel mobile payments (Kenya, Uganda, Tanzania, etc.)", "icon": "A", "color": "#ED1C24", "category": "mobile", "enabled": false, "regions": ["KE", "UG", "TZ", "MW", "ZM", "RW", "CD"]},
  {"id": "orange_money", "name": "Orange Money", "description": "Orange mobile payments (West & Central Africa)", "icon": "O", "color": "#FF6600", "category": "mobile", "enabled": false, "regions": ["SN", "ML", "CI", "BF", "CM", "GN", "MG"]},
  {"id": "wave", "name": "Wave", "description": "Wave mobile money (Senegal, Côte d Ivoire)", "icon": "W", "color": "#1DC4E9", "category": "mobile", "enabled": false, "regions": ["SN", "CI", "ML", "BF", "GM", "UG"]},
  {"id": "flutterwave", "name": "Flutterwave", "description": "African payment gateway (cards, bank, mobile money)", "icon": "FW", "color": "#F5A623", "category": "card", "enabled": false, "regions": ["NG", "GH", "KE", "ZA", "UG", "TZ", "RW"]},
  {"id": "paystack", "name": "Paystack", "description": "African payment gateway (Nigeria, Ghana, South Africa)", "icon": "PS", "color": "#00C3F7", "category": "card", "enabled": false, "regions": ["NG", "GH", "ZA"]},
  {"id": "apple_pay", "name": "Apple Pay", "description": "Accept Apple Pay (requires Stripe or similar)", "icon": "", "color": "#000000", "category": "wallet", "enabled": false, "regions": []},
  {"id": "google_pay", "name": "Google Pay", "description": "Accept Google Pay (requires Stripe or similar)", "icon": "G", "color": "#4285F4", "category": "wallet", "enabled": false, "regions": []},
  {"id": "bank_transfer", "name": "Bank Transfer", "description": "Accept direct bank transfers", "icon": "BK", "color": "#2C3E50", "category": "bank", "enabled": false, "regions": []},
  {"id": "bitcoin", "name": "Bitcoin", "description": "Accept Bitcoin payments", "icon": "₿", "color": "#F7931A", "category": "crypto", "enabled": false, "regions": []},
  {"id": "klarna", "name": "Klarna", "description": "Buy now, pay later (Europe, US)", "icon": "K", "color": "#FFB3C7", "category": "wallet", "enabled": false, "regions": ["US", "GB", "DE", "SE", "NO", "FI", "DK", "NL", "BE", "AT", "CH", "AU"]},
  {"id": "afterpay", "name": "Afterpay/Clearpay", "description": "Buy now, pay later installments", "icon": "AP", "color": "#B2FCE4", "category": "wallet", "enabled": false, "regions": ["US", "AU", "NZ", "GB", "CA"]}
]'

TIMEZONES='[
  {"value": "UTC", "label": "UTC (Coordinated Universal Time)"},
  {"value": "America/New_York", "label": "Eastern Time (US & Canada)"},
  {"value": "America/Chicago", "label": "Central Time (US & Canada)"},
  {"value": "America/Denver", "label": "Mountain Time (US & Canada)"},
  {"value": "America/Los_Angeles", "label": "Pacific Time (US & Canada)"},
  {"value": "Europe/London", "label": "London"},
  {"value": "Europe/Paris", "label": "Paris"},
  {"value": "Europe/Berlin", "label": "Berlin"},
  {"value": "Africa/Lagos", "label": "Lagos"},
  {"value": "Africa/Johannesburg", "label": "Johannesburg"},
  {"value": "Africa/Nairobi", "label": "Nairobi"},
  {"value": "Africa/Cairo", "label": "Cairo"},
  {"value": "Asia/Dubai", "label": "Dubai"},
  {"value": "Asia/Singapore", "label": "Singapore"},
  {"value": "Asia/Tokyo", "label": "Tokyo"},
  {"value": "Australia/Sydney", "label": "Sydney"}
]'

DATE_FORMATS='[
  {"value": "MM/DD/YYYY", "label": "MM/DD/YYYY (US)"},
  {"value": "DD/MM/YYYY", "label": "DD/MM/YYYY (Europe)"},
  {"value": "YYYY-MM-DD", "label": "YYYY-MM-DD (ISO)"},
  {"value": "DD.MM.YYYY", "label": "DD.MM.YYYY (Germany)"},
  {"value": "YYYY/MM/DD", "label": "YYYY/MM/DD (Japan)"}
]'

SHIPPING_SETTINGS='{"freeShippingThreshold": 100, "defaultRate": 9.99, "zones": []}'

NOTIFICATION_SETTINGS='{"newOrder": true, "lowStock": true, "customerRegistration": false, "orderStatus": true, "newsletter": false}'

STORE_SETTINGS='{"enableGuestCheckout": false, "showOutOfStock": true, "enableReviews": true, "enableWishlist": true, "enableCompare": false, "itemsPerPage": 12, "defaultSort": "newest"}'

# Update entry with new data
echo "📤 Updating site_settings entry with sample data..."
UPDATE_ENTRY_RESPONSE=$(curl -s -X PATCH "${CMS_URL}/api/v1/content/entries/${ENTRY_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"data\": {
      \"payment_methods\": ${PAYMENT_METHODS},
      \"timezones\": ${TIMEZONES},
      \"date_formats\": ${DATE_FORMATS},
      \"shipping_settings\": ${SHIPPING_SETTINGS},
      \"notification_settings\": ${NOTIFICATION_SETTINGS},
      \"store_settings\": ${STORE_SETTINGS}
    }
  }")

if echo "$UPDATE_ENTRY_RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
  echo "✅ Site settings entry updated with new data!"
  echo ""
  echo "🎉 Schema and data update complete!"
else
  echo "❌ Failed to update site_settings entry:"
  echo "$UPDATE_ENTRY_RESPONSE" | jq .
  exit 1
fi
