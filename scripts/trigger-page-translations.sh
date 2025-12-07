#!/bin/bash

# Trigger translations for all page entries
# This ensures pages are translated to enabled locales (fr, es, de, etc.)

API_URL="${CMS_API_URL:-http://localhost:8000}"
API_KEY="${CMS_API_KEY:-bk_p4mPH5PGxFb9yk3jd9O12ChtBcCt8fGfDlagg70tobI}"

echo "Triggering translations for page entries..."
echo "API URL: $API_URL"

# Get French locale ID (main non-English locale)
FR_LOCALE_ID=$(curl -s "$API_URL/api/v1/translation/locales" \
    -H "X-API-Key: $API_KEY" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for loc in data:
    if loc['code'] == 'fr':
        print(loc['id'])
        break
" 2>/dev/null)

if [ -z "$FR_LOCALE_ID" ]; then
    echo "Error: Could not find French locale ID"
    exit 1
fi

echo "French locale ID: $FR_LOCALE_ID"

# Get all page entries
echo ""
echo "Fetching page entries..."
PAGE_IDS=$(curl -s "$API_URL/api/v1/content/entries?content_type_slug=page&limit=50" \
    -H "X-API-Key: $API_KEY" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for item in data.get('items', []):
    print(f\"{item['id']}|{item['slug']}\")
" 2>/dev/null)

if [ -z "$PAGE_IDS" ]; then
    echo "No page entries found"
    exit 1
fi

# Translate each page
echo ""
echo "=== Triggering Translations ==="
while IFS='|' read -r entry_id slug; do
    echo ""
    echo "Translating: $slug ($entry_id)"

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/api/v1/translation/translate" \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $API_KEY" \
        -d "{
            \"content_entry_id\": \"$entry_id\",
            \"target_locale_ids\": [\"$FR_LOCALE_ID\"],
            \"force_retranslate\": false,
            \"incremental\": false
        }")

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo "✓ Translation triggered for: $slug"
    else
        echo "✗ Failed to translate: $slug (HTTP $http_code)"
        # Show error details for debugging
        echo "  $(echo "$body" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('detail', d.get('message', 'Unknown error')))" 2>/dev/null || echo "$body" | head -c 100)"
    fi
done <<< "$PAGE_IDS"

echo ""
echo "========================================"
echo "Translation requests complete!"
echo "========================================"
echo ""
echo "Note: Translations may take a moment to process."
echo "The CMS will auto-translate content using Google Translate."
