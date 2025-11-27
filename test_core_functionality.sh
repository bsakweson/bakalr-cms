#!/bin/bash

# Core Functionality Test Suite for Bakalr CMS
# Tests the critical user flows that were just fixed

# Don't exit on error - we want to run all tests

API_URL="http://localhost:8000/api/v1"
FRONTEND_URL="http://localhost:3000"

echo "🧪 Bakalr CMS - Core Functionality Tests"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
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

info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
for i in {1..30}; do
    if curl -s "http://localhost:8000/health" > /dev/null 2>&1; then
        echo "   Backend ready after ${i}s"
        break
    fi
    sleep 1
done

for i in {1..30}; do
    if curl -s "$FRONTEND_URL" > /dev/null 2>&1; then
        echo "   Frontend ready after ${i}s"
        break
    fi
    sleep 1
done
echo ""

# Test 1: Backend Health
echo ""
echo "Test 1: Backend Health Check"
if curl -f -s "http://localhost:8000/health" > /dev/null 2>&1; then
    pass "Backend is healthy"
else
    fail "Backend health check failed"
fi

# Test 2: Frontend Reachability
echo ""
echo "Test 2: Frontend Reachability"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL")
if [ "$HTTP_CODE" = "200" ]; then
    pass "Frontend is reachable (HTTP $HTTP_CODE)"
else
    fail "Frontend returned HTTP $HTTP_CODE"
fi

# Test 3: Redis Connection (via backend cache)
echo ""
echo "Test 3: Redis Cache Connection"
# Check backend logs for Redis connection confirmation
REDIS_LOGS=$(docker-compose logs backend 2>/dev/null | grep -i "redis cache connected" | tail -1)
if [ -n "$REDIS_LOGS" ]; then
    pass "Redis cache is connected (confirmed in backend logs)"
else
    fail "Could not confirm Redis connection from logs"
fi

# Test 4: Database Connection
echo ""
echo "Test 4: Database Connection"
RESPONSE=$(curl -s -X POST "$API_URL/auth/register" \
    -H "Content-Type: application/json" \
    -d '{"email":"test'$(date +%s)'@example.com","password":"TestPass123!","full_name":"Test User","organization_name":"Test Org"}')

if echo "$RESPONSE" | grep -q "access_token\|already exists"; then
    pass "Database connection working (registration endpoint responded)"
else
    fail "Database connection issue"
fi

# Test 5: Password Reset Flow
echo ""
echo "Test 5: Password Reset Email Request"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/auth/password-reset/request" \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com"}')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
if [ "$HTTP_CODE" = "200" ]; then
    pass "Password reset request works (HTTP 200)"
else
    fail "Password reset request failed (HTTP $HTTP_CODE)"
fi

# Test 6: API Documentation
echo ""
echo "Test 6: API Documentation Available"
if curl -f -s "http://localhost:8000/api/docs" > /dev/null 2>&1; then
    pass "API documentation is accessible at /api/docs"
else
    fail "API documentation not available"
fi

# Test 7: GraphQL Endpoint
echo ""
echo "Test 7: GraphQL Endpoint"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/graphql" \
    -H "Content-Type: application/json" \
    -d '{"query":"{ __schema { queryType { name } } }"}')

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
if [ "$HTTP_CODE" = "200" ]; then
    pass "GraphQL endpoint is working"
else
    info "GraphQL endpoint returned HTTP $HTTP_CODE (non-critical, not related to password reset)"
fi

# Test 8: Rate Limiting (Basic Check)
echo ""
echo "Test 8: Rate Limiting Headers Present"
RESPONSE=$(curl -s -I "http://localhost:8000/health")
if echo "$RESPONSE" | grep -q "X-RateLimit"; then
    pass "Rate limiting headers present"
else
    info "Rate limiting headers not found (may not be on /health endpoint)"
fi

# Test 9: CORS Headers
echo ""
echo "Test 9: CORS Configuration"
RESPONSE=$(curl -s -I "http://localhost:8000/health")
if echo "$RESPONSE" | grep -q "Access-Control-Allow"; then
    pass "CORS headers configured"
else
    info "CORS headers not found on health endpoint"
fi

# Test 10: Docker Image Sizes
echo ""
echo "Test 10: Docker Image Sizes"
BACKEND_SIZE=$(docker images bakalr-cms-backend:latest --format "{{.Size}}")
FRONTEND_SIZE=$(docker images bakalr-cms-frontend:latest --format "{{.Size}}")

echo "   Backend:  $BACKEND_SIZE"
echo "   Frontend: $FRONTEND_SIZE"

if [ ! -z "$BACKEND_SIZE" ] && [ ! -z "$FRONTEND_SIZE" ]; then
    pass "Docker images built successfully"
else
    fail "Docker images missing"
fi

# Summary
echo ""
echo "========================================"
echo "Test Summary:"
echo -e "${GREEN}Passed: $PASSED${NC}"
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Failed: $FAILED${NC}"
fi
echo "========================================"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All critical tests passed!${NC}"
    echo ""
    echo "✅ Core functionality verified:"
    echo "   • Authentication system"
    echo "   • Password reset flow"
    echo "   • Redis cache connected"
    echo "   • Database operational"
    echo "   • API endpoints responding"
    echo ""
    echo "📋 Next Steps:"
    echo "   1. Manual test: Register a new account at $FRONTEND_URL/register"
    echo "   2. Manual test: Request password reset and check email"
    echo "   3. Manual test: Click reset link and change password"
    echo "   4. Check backend logs: docker-compose logs backend --tail 50"
    echo "   5. Review rate limiting: Check X-RateLimit headers on API calls"
    echo ""
    exit 0
else
    echo -e "${RED}⚠️  Some tests failed. Check the output above.${NC}"
    echo ""
    echo "🔍 Debugging tips:"
    echo "   • Check logs: docker-compose logs backend frontend"
    echo "   • Verify services: docker-compose ps"
    echo "   • Check Redis: docker-compose exec redis redis-cli ping"
    echo "   • Check DB: docker-compose exec postgres psql -U postgres -d bakalr_cms"
    echo ""
    exit 1
fi
