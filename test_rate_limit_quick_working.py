#!/usr/bin/env python3
"""
Quick rate limiting test - checks if rate limiting actually works
"""
import requests
import time

BASE_URL = "http://localhost:8000"

def test_health_rate_limit():
    """Test if /health endpoint enforces rate limits"""
    print("Testing /health endpoint rate limiting...")
    print("Making 150 rapid requests (limit is 100/minute)...\n")
    
    successes = 0
    rate_limited = 0
    
    for i in range(150):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=2)
            
            # Check for rate limit headers
            if i == 0:
                print("First request headers:")
                for header in ["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]:
                    value = response.headers.get(header, "NOT PRESENT")
                    print(f"  {header}: {value}")
                print()
            
            if response.status_code == 200:
                successes += 1
                if i % 20 == 0:
                    remaining = response.headers.get("X-RateLimit-Remaining", "?")
                    print(f"  Request {i+1:3d}: ✅ OK (Remaining: {remaining})")
            elif response.status_code == 429:
                rate_limited += 1
                if rate_limited == 1:
                    print(f"\n🛑 Rate limit hit at request {i+1}!")
                    retry_after = response.headers.get("Retry-After", "?")
                    print(f"   Retry-After: {retry_after}s\n")
            
            time.sleep(0.01)  # 10ms between requests = 100 req/second
            
        except Exception as e:
            print(f"  Request {i+1}: ❌ Error: {e}")
            break
    
    print(f"\n" + "="*60)
    print(f"Results:")
    print(f"  Total requests: {successes + rate_limited}")
    print(f"  Successful: {successes}")
    print(f"  Rate limited: {rate_limited}")
    print("="*60)
    
    if rate_limited > 0:
        print(f"\n✅ Rate limiting is WORKING! Hit limit after {successes} requests")
        return True
    else:
        print(f"\n❌ Rate limiting NOT working - all {successes} requests succeeded")
        return False


def test_authenticated_endpoint():
    """Test rate limiting on authenticated endpoint"""
    print("\n\nTesting authenticated endpoint rate limiting...")
    
    # Login first
    try:
        login_response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "admin@bakalr.cms", "password": "admin123"},
            timeout=5
        )
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            return False
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        print(f"✅ Logged in successfully")
        print(f"Making 120 rapid requests to /api/v1/content/entries...\n")
        
        successes = 0
        rate_limited = 0
        
        for i in range(120):
            try:
                response = requests.get(
                    f"{BASE_URL}/api/v1/content/entries",
                    headers=headers,
                    timeout=2
                )
                
                # Check for rate limit headers on first request
                if i == 0:
                    print("First request headers:")
                    for header in ["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"]:
                        value = response.headers.get(header, "NOT PRESENT")
                        print(f"  {header}: {value}")
                    print()
                
                if response.status_code == 200:
                    successes += 1
                    if i % 20 == 0:
                        remaining = response.headers.get("X-RateLimit-Remaining", "?")
                        print(f"  Request {i+1:3d}: ✅ OK (Remaining: {remaining})")
                elif response.status_code == 429:
                    rate_limited += 1
                    if rate_limited == 1:
                        print(f"\n🛑 Rate limit hit at request {i+1}!")
                        retry_after = response.headers.get("Retry-After", "?")
                        print(f"   Retry-After: {retry_after}s\n")
                
                time.sleep(0.01)  # 10ms between requests
                
            except Exception as e:
                print(f"  Request {i+1}: ❌ Error: {e}")
                break
        
        print(f"\n" + "="*60)
        print(f"Results:")
        print(f"  Total requests: {successes + rate_limited}")
        print(f"  Successful: {successes}")
        print(f"  Rate limited: {rate_limited}")
        print("="*60)
        
        if rate_limited > 0:
            print(f"\n✅ Authenticated rate limiting is WORKING!")
            return True
        else:
            print(f"\n❌ Authenticated rate limiting NOT working")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    print("="*60)
    print("RATE LIMITING QUICK TEST")
    print("="*60)
    
    result1 = test_health_rate_limit()
    result2 = test_authenticated_endpoint()
    
    print("\n" + "="*60)
    if result1 and result2:
        print("🎉 ALL TESTS PASSED - Rate limiting is working!")
    else:
        print("⚠️  Some tests failed - rate limiting may not be configured correctly")
    print("="*60)
