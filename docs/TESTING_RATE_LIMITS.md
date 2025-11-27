# Testing Rate Limiting - Quick Guide

## Prerequisites

1. **Redis must be running** (required for rate limiting)
2. **Backend server must be running**

## Quick Setup

### 1. Start Redis

```bash
# Install Redis (if not installed)
brew install redis

# Start Redis
brew services start redis

# Verify Redis is running
redis-cli ping
# Should return: PONG
```

### 2. Start Backend Server

```bash
# Option 1: Using Poetry (development)
poetry run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Option 2: Using VS Code Task
# Press Cmd+Shift+P → "Tasks: Run Task" → "Start Backend Server"
```

## Manual Testing with curl

### Test 1: Login Endpoint Rate Limit (10 requests/minute)

```bash
# Send 15 requests to trigger rate limit
for i in {1..15}; do
  echo "Request $i:"
  curl -s -w "\nStatus: %{http_code}\n\n" -X POST \
    http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"wrong"}'
  sleep 0.2
done
```

**Expected Result:**
- Requests 1-10: HTTP 401 (Unauthorized) or 422 (Validation Error)
- Request 11+: HTTP 429 (Too Many Requests)

**Success Indicators:**
- HTTP 429 response
- Response body: `{"detail": "Rate limit exceeded: 100 per hour"}`
- Header `Retry-After` with seconds until reset

### Test 2: Check Rate Limit Headers

```bash
curl -i -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"wrong"}'
```

**Look for these headers:**
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1700000000
```

### Test 3: GraphQL Rate Limit (100 requests/minute)

```bash
# Send 105 requests to trigger GraphQL rate limit
for i in {1..105}; do
  if [ $((i % 10)) -eq 0 ]; then echo "Request $i"; fi
  response=$(curl -s -w "\n%{http_code}" -X POST \
    http://localhost:8000/api/v1/graphql \
    -H "Content-Type: application/json" \
    -d '{"query":"query { __typename }"}')
  status=$(echo "$response" | tail -1)
  if [ "$status" = "429" ]; then
    echo "✓ Rate limited at request $i"
    echo "$response" | head -n-1
    break
  fi
  sleep 0.05
done
```

**Expected Result:**
- Requests 1-100: HTTP 200
- Request 101+: HTTP 429

## Automated Test Script

### Using the Test Script

```bash
# Make script executable
chmod +x test_rate_limits.sh

# Run tests
./test_rate_limits.sh
```

### Expected Output

```text
═══════════════════════════════════════════════
   Rate Limiting Test Suite
═══════════════════════════════════════════════

Test 1: Login Rate Limit
Endpoint: POST http://localhost:8000/api/v1/auth/login
Expected: Rate limited after ~10 requests per minute

Request 1: Status 401
Request 2: Status 401
...
Request 10: Status 401
✓ Rate limited at request 11
Response: {"detail":"Rate limit exceeded: 100 per hour"}

✓ Login rate limiting is working!
Limited after 10 successful requests
```

## Troubleshooting

### Issue: Rate limiting not working

**Check 1: Is Redis running?**
```bash
redis-cli ping
# Should return: PONG
```

**If not running:**
```bash
brew services start redis
```

**Check 2: Is backend connected to Redis?**
```bash
# Check backend logs for Redis connection
tail -f backend/logs/app.log | grep -i redis
```

**Check 3: Rate limiting enabled in config?**
```bash
grep RATE_LIMIT .env
# Should show: RATE_LIMIT_ENABLED=true
```

### Issue: Backend not starting

**Check if port 8000 is already in use:**
```bash
lsof -i :8000
```

**Kill existing process:**
```bash
lsof -ti:8000 | xargs kill -9
```

**Restart backend:**
```bash
poetry run uvicorn backend.main:app --reload --port 8000
```

### Issue: Getting connection errors

**Ensure backend is accessible:**
```bash
curl http://localhost:8000/api/docs
# Should return HTML
```

## Verification Checklist

Before testing, verify:

- [ ] Redis is running (`redis-cli ping` returns `PONG`)
- [ ] Backend server is running (port 8000)
- [ ] `.env` has `RATE_LIMIT_ENABLED=true`
- [ ] `.env` has `REDIS_URL=redis://localhost:6379/0`
- [ ] No firewall blocking localhost connections

## Rate Limit Configuration

Current limits from `.env.example`:

| Endpoint Type | Per Hour | Per Minute |
|--------------|----------|------------|
| Login | 100 | 10 |
| Register | 10 | 2 |
| Password Reset | 10 | 2 |
| 2FA Verify | 100 | 20 |
| Content Create | 200 | 50 |
| Content List | 1000 | 200 |
| Media Upload | 100 | 20 |
| GraphQL | 1000 | 100 |

## Advanced Testing

### Test Different Identifiers

**Test by IP address (anonymous):**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test","password":"test"}'
```

**Test by User ID (authenticated):**
```bash
# First, get a token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com","password":"yourpassword"}' \
  | jq -r .access_token)

# Then make requests with token
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/content/entries
```

**Test by API Key:**
```bash
curl -H "X-API-Key: your-api-key" \
  http://localhost:8000/api/v1/content/entries
```

### Monitor Redis Keys

Watch rate limit keys being created in Redis:

```bash
redis-cli MONITOR | grep ratelimit
```

### Check Rate Limit Counters

```bash
# List all rate limit keys
redis-cli KEYS "ratelimit:*"

# Check specific counter
redis-cli GET "ratelimit:ip:127.0.0.1:/api/v1/auth/login:minute"
```

## Success Criteria

Rate limiting is working correctly when:

1. ✅ Requests are rate limited after reaching the configured limit
2. ✅ HTTP 429 status code is returned when rate limited
3. ✅ Response includes rate limit details in body
4. ✅ `Retry-After` header is present in 429 responses
5. ✅ Rate limit headers are present in successful responses
6. ✅ Different endpoints have different limits
7. ✅ Rate limits reset after the time window expires

## Next Steps

After successful testing:

1. **Monitor in Production**: Set up monitoring for rate limit hits
2. **Adjust Limits**: Based on actual usage patterns, adjust limits in `.env`
3. **Add Alerts**: Alert on excessive rate limit hits (potential abuse)
4. **Document for Users**: Inform API consumers of rate limits
5. **Implement Whitelisting**: For trusted IPs or premium users

## Resources

- Rate Limiting Completion Report: `docs/RATE_LIMITING_COMPLETION.md`
- GraphQL Security: `docs/GRAPHQL_SECURITY_IMPLEMENTATION.md`
- Backend Logs: Check `backend/logs/` for rate limit events
- Redis: `redis-cli` for debugging rate limit keys
