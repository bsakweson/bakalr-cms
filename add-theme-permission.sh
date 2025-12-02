#!/bin/bash

# Add themes.read permission to boutique API key

# First, login to get JWT token
echo "Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "bsakweson@gmail.com",
    "password": "Angelbenise123!@"
  }')

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
  echo "❌ Login failed"
  echo $LOGIN_RESPONSE | jq .
  exit 1
fi

echo "✅ Logged in successfully"

# List API keys to find the boutique key
echo -e "\nFinding boutique API key..."
API_KEYS=$(curl -s "http://localhost:8000/api/v1/api-keys?page_size=50" \
  -H "Authorization: Bearer $TOKEN")

KEY_ID=$(echo $API_KEYS | jq -r '.items[] | select(.name == "boutique apikey") | .id')

if [ -z "$KEY_ID" ] || [ "$KEY_ID" = "null" ]; then
  echo "❌ Could not find boutique API key"
  exit 1
fi

echo "✅ Found API key: $KEY_ID"

# Show current permissions
CURRENT_SCOPES=$(echo $API_KEYS | jq -r '.items[] | select(.name == "boutique apikey") | .scopes')
echo "Current permissions: $CURRENT_SCOPES"

# Add themes.read permission
echo -e "\nAdding themes.read permission..."
RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/api-keys/$KEY_ID/permissions" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '["themes.read"]')

echo $RESPONSE | jq .

# Verify the permission was added
echo -e "\nVerifying updated permissions..."
UPDATED_KEY=$(curl -s "http://localhost:8000/api/v1/api-keys/$KEY_ID" \
  -H "Authorization: Bearer $TOKEN")

echo $UPDATED_KEY | jq '.scopes'

echo -e "\n✅ Done!"
