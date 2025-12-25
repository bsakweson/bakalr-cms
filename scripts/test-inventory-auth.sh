#!/bin/bash
# Test Inventory Service Authentication
# Usage: ./scripts/test-inventory-auth.sh

set -e

echo "=== Bakalr CMS → Inventory Service Auth Test ==="
echo ""

# Prompt for credentials
read -p "Email: " EMAIL
read -s -p "Password: " PASSWORD
echo ""
echo ""

# Authenticate with CMS backend
echo "🔐 Authenticating with CMS..."
AUTH_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"${EMAIL}\",\"password\":\"${PASSWORD}\"}")

# Extract token
TOKEN=$(echo "$AUTH_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "❌ Authentication failed!"
  echo "Response: $AUTH_RESPONSE"
  exit 1
fi

echo "✅ Got JWT token: ${TOKEN:0:50}..."
echo ""

# Decode and show JWT claims
echo "📋 JWT Claims:"
ORG_ID=$(echo "$TOKEN" | cut -d. -f2 | python3 -c "
import sys, base64, json
payload = sys.stdin.read().strip()
payload += '=' * (4 - len(payload) % 4)
decoded = json.loads(base64.urlsafe_b64decode(payload))
print(decoded.get('org_id', ''))
")
echo "$TOKEN" | cut -d. -f2 | python3 -c "
import sys, base64, json
payload = sys.stdin.read().strip()
payload += '=' * (4 - len(payload) % 4)
decoded = json.loads(base64.urlsafe_b64decode(payload))
print(f'   Issuer (iss): {decoded.get(\"iss\")}')
print(f'   Subject (sub): {decoded.get(\"sub\")}')
print(f'   Org ID: {decoded.get(\"org_id\")}')
"
echo ""

# Test inventory service
echo "📦 Testing Inventory Service at https://bakalr.com/api/v1/inventory/items..."
INVENTORY_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: $ORG_ID" \
  "https://bakalr.com/api/v1/inventory/items")

HTTP_CODE=$(echo "$INVENTORY_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$INVENTORY_RESPONSE" | sed '/HTTP_CODE:/d')

echo "HTTP Status: $HTTP_CODE"
echo "Response:"
echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY" | head -c 500
echo ""

if [ "$HTTP_CODE" = "200" ]; then
  echo "✅ Inventory service authentication works!"
elif [ "$HTTP_CODE" = "401" ]; then
  echo "❌ 401 Unauthorized - Inventory service rejected the CMS token"
  echo "   The services may use different JWT secrets"
else
  echo "⚠️  Got HTTP $HTTP_CODE"
fi
