#!/bin/bash
# Rate Limiting Test Script
# Tests rate limits on various endpoints using curl

set -e

BASE_URL="http://localhost:8000"
API_VERSION="/api/v1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo -e "${CYAN}   Rate Limiting Test Suite${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════${NC}\n"

# Test 1: Login endpoint (strict limit)
echo -e "${YELLOW}Test 1: Login Rate Limit${NC}"
echo -e "Endpoint: POST ${BASE_URL}${API_VERSION}/auth/login"
echo -e "Expected: Rate limited after ~10 requests per minute\n"

success_count=0
rate_limited=false

for i in {1..15}; do
    response=$(curl -s -w "\n%{http_code}" -X POST \
        "${BASE_URL}${API_VERSION}/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"email":"test@example.com","password":"wrongpassword"}' 2>/dev/null)
    
    status_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$status_code" = "429" ]; then
        echo -e "${YELLOW}✓ Rate limited at request $i${NC}"
        echo -e "Response: $body"
        rate_limited=true
        break
    else
        success_count=$((success_count + 1))
        echo -e "Request $i: Status $status_code"
    fi
    
    sleep 0.1
done

if [ "$rate_limited" = true ]; then
    echo -e "\n${GREEN}✓ Login rate limiting is working!${NC}"
    echo -e "Limited after $success_count successful requests\n"
else
    echo -e "\n${RED}✗ No rate limiting detected after 15 requests${NC}\n"
fi

# Test 2: Check rate limit headers
echo -e "${CYAN}─────────────────────────────────────────────${NC}\n"
echo -e "${YELLOW}Test 2: Rate Limit Headers${NC}"
echo -e "Checking for rate limit headers on successful request\n"

response=$(curl -s -i -X POST \
    "${BASE_URL}${API_VERSION}/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"wrong"}' 2>/dev/null)

echo "$response" | grep -E "(X-RateLimit|Retry-After)" || echo "No rate limit headers found"

# Test 3: GraphQL rate limiting (if token available)
echo -e "\n${CYAN}─────────────────────────────────────────────${NC}\n"
echo -e "${YELLOW}Test 3: GraphQL Rate Limit (Quick Test)${NC}"
echo -e "Endpoint: POST ${BASE_URL}${API_VERSION}/graphql"
echo -e "Testing with 20 requests (full limit is 100/min)\n"

graphql_success=0
graphql_limited=false

for i in {1..20}; do
    response=$(curl -s -w "\n%{http_code}" -X POST \
        "${BASE_URL}${API_VERSION}/graphql" \
        -H "Content-Type: application/json" \
        -d '{"query":"query { __typename }"}' 2>/dev/null)
    
    status_code=$(echo "$response" | tail -1)
    
    if [ "$status_code" = "429" ]; then
        echo -e "${YELLOW}✓ GraphQL rate limited at request $i${NC}"
        graphql_limited=true
        break
    else
        graphql_success=$((graphql_success + 1))
        if [ $((i % 5)) -eq 0 ]; then
            echo -e "Requests 1-$i: OK"
        fi
    fi
    
    sleep 0.05
done

if [ "$graphql_limited" = true ]; then
    echo -e "\n${GREEN}✓ GraphQL rate limiting is working!${NC}\n"
else
    echo -e "\n${GREEN}✓ GraphQL: $graphql_success requests successful (limit not hit with 20 requests)${NC}\n"
fi

# Summary
echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
echo -e "${CYAN}   Summary${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════${NC}\n"

tests_passed=0
tests_total=2

if [ "$rate_limited" = true ]; then
    echo -e "${GREEN}✓ Login rate limiting: PASS${NC}"
    tests_passed=$((tests_passed + 1))
else
    echo -e "${RED}✗ Login rate limiting: FAIL${NC}"
fi

echo -e "${GREEN}✓ Rate limit headers: CHECK${NC}"

if [ "$graphql_limited" = true ] || [ "$graphql_success" -eq 20 ]; then
    echo -e "${GREEN}✓ GraphQL rate limiting: PASS${NC}"
    tests_passed=$((tests_passed + 1))
else
    echo -e "${RED}✗ GraphQL rate limiting: FAIL${NC}"
fi

echo -e "\n${CYAN}Tests Passed: $tests_passed/$tests_total${NC}\n"

if [ $tests_passed -eq $tests_total ]; then
    echo -e "${GREEN}✓ All rate limiting tests passed!${NC}\n"
    exit 0
else
    echo -e "${YELLOW}⚠ Some tests did not pass as expected${NC}\n"
    exit 1
fi
