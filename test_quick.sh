#!/bin/bash

# Quick Test Suite - Silent curl outputs
# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

API_URL="http://localhost:8000/api/v1"
PASSED=0
FAILED=0

# Helper functions
pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

echo "========================================="
echo "Bakalr CMS - Quick Test Suite"
echo "========================================="
echo ""

# Wait for services
echo "⏳ Waiting for services..."
for i in {1..30}; do
    if curl -sf "http://localhost:8000/health" >/dev/null 2>&1; then
        echo "   Services ready"
        break
    fi
    sleep 1
done
echo ""

# Test 1: Backend Health
echo "Test 1: Backend Health"
if curl -sf "http://localhost:8000/health" >/dev/null 2>&1; then
    pass "Backend is healthy"
else
    fail "Backend health check failed"
fi

# Test 2: Frontend
echo ""
echo "Test 2: Frontend"
HTTP_CODE=$(curl -so /dev/null -w "%{http_code}" "http://localhost:3000" 2>/dev/null)
if [ "$HTTP_CODE" = "200" ]; then
    pass "Frontend reachable (HTTP $HTTP_CODE)"
else
    fail "Frontend returned HTTP $HTTP_CODE"
fi

# Test 3: Redis (check logs)
echo ""
echo "Test 3: Redis Cache"
if docker-compose logs backend 2>/dev/null | grep -q "Redis cache connected"; then
    pass "Redis cache connected"
else
    fail "Redis connection not confirmed"
fi

# Test 4: Database
echo ""
echo "Test 4: Database"
RESPONSE=$(curl -s "$API_URL/auth/register" \
    -H "Content-Type: application/json" \
    -d '{"email":"test'$(date +%s)'@example.com","password":"TestPass123!","full_name":"Test","organization_name":"Test"}' 2>/dev/null)

if echo "$RESPONSE" | grep -q "access_token\|already exists"; then
    pass "Database working"
else
    fail "Database connection issue"
fi

# Test 5: Password Reset
echo ""
echo "Test 5: Password Reset"
HTTP_CODE=$(curl -so /dev/null -w "%{http_code}" -X POST "$API_URL/auth/password-reset/request" \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com"}' 2>/dev/null)

if [ "$HTTP_CODE" = "200" ]; then
    pass "Password reset works (HTTP 200)"
else
    fail "Password reset failed (HTTP $HTTP_CODE)"
fi

# Test 6: API Docs
echo ""
echo "Test 6: API Documentation"
HTTP_CODE=$(curl -so /dev/null -w "%{http_code}" "http://localhost:8000/api/docs" 2>/dev/null)
if [ "$HTTP_CODE" = "200" ]; then
    pass "API docs accessible"
else
    fail "API docs returned HTTP $HTTP_CODE"
fi

# Test 7: GraphQL
echo ""
echo "Test 7: GraphQL"
HTTP_CODE=$(curl -so /dev/null -w "%{http_code}" -X POST "$API_URL/graphql" \
    -H "Content-Type: application/json" \
    -d '{"query":"{ __schema { queryType { name } } }"}' 2>/dev/null)

if [ "$HTTP_CODE" = "200" ]; then
    pass "GraphQL endpoint working"
else
    fail "GraphQL failed (HTTP $HTTP_CODE)"
fi

# Test 8: Docker Images
echo ""
echo "Test 8: Docker Images"
BACKEND_SIZE=$(docker images bakalr-cms-backend --format "{{.Size}}" 2>/dev/null | head -1)
FRONTEND_SIZE=$(docker images bakalr-cms-frontend --format "{{.Size}}" 2>/dev/null | head -1)

if [ -n "$BACKEND_SIZE" ] && [ -n "$FRONTEND_SIZE" ]; then
    echo "   Backend:  $BACKEND_SIZE"
    echo "   Frontend: $FRONTEND_SIZE"
    pass "Docker images built"
else
    fail "Docker images not found"
fi

# Summary
echo ""
echo "========================================="
echo "Test Summary:"
echo "  Passed: $PASSED"
echo "  Failed: $FAILED"
echo "========================================="

exit 0
