#!/bin/bash
# Update site_settings content type to add symbol field and update with currency data

set -e

API_URL="http://localhost:8000/api/v1"
EMAIL="bsakweson@gmail.com"
PASSWORD="Angelbenise1"

echo "=== Logging in to CMS ==="
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}")

TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "Failed to get token. Response:"
  echo "$LOGIN_RESPONSE"
  exit 1
fi

echo "Token obtained successfully"

echo ""
echo "=== Updating site_settings content type ==="
curl -s -X PATCH "$API_URL/content/types/8668a69c-2d91-43fe-8bb0-7b517855ef8f" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "fields": [
      {"name": "site_name", "type": "text", "required": true, "localized": true, "help_text": "Site name - IS translated"},
      {"name": "tagline", "type": "text", "required": false, "localized": true, "help_text": "Site tagline - IS translated"},
      {"name": "logo_id", "type": "media", "required": false, "help_text": "Site logo"},
      {"name": "favicon_id", "type": "media", "required": false, "help_text": "Favicon"},
      {"name": "default_locale", "type": "text", "required": true, "localized": false, "default": "en", "help_text": "Default locale code"},
      {"name": "enabled_locales", "type": "json", "required": true, "localized": false, "help_text": "Array of locale codes"},
      {"name": "default_currency", "type": "text", "required": true, "localized": false, "default": "USD", "help_text": "Default currency code"},
      {"name": "symbol", "type": "text", "required": false, "localized": false, "default": "$", "help_text": "Default currency symbol"},
      {"name": "enabled_currencies", "type": "json", "required": false, "localized": false, "help_text": "Array of currency objects with code, symbol, name, flag, exchange_rate"},
      {"name": "contact_email", "type": "text", "required": false, "localized": false, "help_text": "Contact email"},
      {"name": "contact_phone", "type": "text", "required": false, "localized": false, "help_text": "Phone number"},
      {"name": "contact_address", "type": "textarea", "required": false, "localized": true, "help_text": "Physical address"},
      {"name": "social_links", "type": "json", "required": false, "localized": false, "help_text": "Social media URLs"},
      {"name": "analytics_ids", "type": "json", "required": false, "localized": false, "help_text": "Analytics IDs"},
      {"name": "maintenance_mode", "type": "boolean", "required": false, "default": false, "help_text": "Enable maintenance mode"},
      {"name": "maintenance_message", "type": "textarea", "required": false, "localized": true, "help_text": "Maintenance message"}
    ]
  }'

echo ""
echo ""
echo "=== Checking for existing site_settings entry ==="
ENTRIES_RESPONSE=$(curl -s "$API_URL/content/entries?content_type_api_id=site_settings" \
  -H "Authorization: Bearer $TOKEN")

echo "Response preview:"
echo "$ENTRIES_RESPONSE" | head -c 300

# Check if there's an existing entry - look for the site_settings specifically
ENTRY_ID=$(echo "$ENTRIES_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    items = data.get('items', [])
    for item in items:
        ct = item.get('content_type', {})
        if ct.get('api_id') == 'site_settings':
            print(item.get('id', ''))
            break
except:
    pass
" 2>/dev/null)

if [ -n "$ENTRY_ID" ] && [ "$ENTRY_ID" != "null" ]; then
  echo ""
  echo ""
  echo "=== Updating existing entry: $ENTRY_ID ==="
  curl -s -X PATCH "$API_URL/content/entries/$ENTRY_ID" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "data": {
        "symbol": "$",
        "enabled_currencies": [
          {"code": "USD", "symbol": "$", "name": "US Dollar", "flag": "🇺🇸", "exchange_rate": 1, "decimal_places": 2, "position": "before"},
          {"code": "EUR", "symbol": "€", "name": "Euro", "flag": "🇪🇺", "exchange_rate": 0.92, "decimal_places": 2, "position": "before"},
          {"code": "MXN", "symbol": "$", "name": "Mexican Peso", "flag": "🇲🇽", "exchange_rate": 17.5, "decimal_places": 2, "position": "before"},
          {"code": "GBP", "symbol": "£", "name": "British Pound", "flag": "🇬🇧", "exchange_rate": 0.79, "decimal_places": 2, "position": "before"},
          {"code": "CAD", "symbol": "CA$", "name": "Canadian Dollar", "flag": "🇨🇦", "exchange_rate": 1.36, "decimal_places": 2, "position": "before"}
        ]
      }
    }'
else
  echo ""
  echo ""
  echo "=== Creating new site_settings entry ==="
  curl -s -X POST "$API_URL/content/entries" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "content_type_id": "8668a69c-2d91-43fe-8bb0-7b517855ef8f",
      "slug": "main-settings",
      "status": "published",
      "data": {
        "site_name": "Bakalr Boutique",
        "tagline": "Your Beauty, Our Passion",
        "default_locale": "en",
        "enabled_locales": ["en", "es", "fr"],
        "default_currency": "USD",
        "symbol": "$",
        "enabled_currencies": [
          {"code": "USD", "symbol": "$", "name": "US Dollar", "flag": "🇺🇸", "exchange_rate": 1, "decimal_places": 2, "position": "before"},
          {"code": "EUR", "symbol": "€", "name": "Euro", "flag": "🇪🇺", "exchange_rate": 0.92, "decimal_places": 2, "position": "before"},
          {"code": "MXN", "symbol": "$", "name": "Mexican Peso", "flag": "🇲🇽", "exchange_rate": 17.5, "decimal_places": 2, "position": "before"},
          {"code": "GBP", "symbol": "£", "name": "British Pound", "flag": "🇬🇧", "exchange_rate": 0.79, "decimal_places": 2, "position": "before"},
          {"code": "CAD", "symbol": "CA$", "name": "Canadian Dollar", "flag": "🇨🇦", "exchange_rate": 1.36, "decimal_places": 2, "position": "before"}
        ],
        "contact_email": "hello@bakalr-boutique.com",
        "contact_phone": "+1 (555) 123-4567",
        "maintenance_mode": false
      }
    }'
fi

echo ""
echo ""
echo "=== Done ==="
