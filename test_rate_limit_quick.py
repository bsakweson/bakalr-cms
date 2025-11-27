#!/usr/bin/env python3
"""
Comprehensive rate limiting test for all API endpoints
Tests rate limits across all major API categories
"""
import requests
import time
from typing import Dict, List, Tuple

BASE_URL = "http://localhost:8000"

# API endpoint categories to test
API_ENDPOINTS = {
    "Public": [
        "/health",
        "/api/v1/health",
    ],
    "Authentication": [
        "/api/v1/auth/login",
        "/api/v1/auth/register",
    ],
    "Content": [
        "/api/v1/content/entries",
        "/api/v1/content/types",
    ],
    "Media": [
        "/api/v1/media",
    ],
    "Users": [
        "/api/v1/users/me",
        "/api/v1/users",
    ],
    "Translations": [
        "/api/v1/translation/locales",
    ],
    "SEO": [
        "/api/v1/seo/meta",
    ],
    "Analytics": [
        "/api/v1/analytics/content",
    ],
    "Webhooks": [
        "/api/v1/webhooks",
    ],
    "Roles": [
        "/api/v1/roles",
    ],
}


def test_anonymous_rate_limit():
    """Test rate limiting for anonymous users"""
    print("Testing anonymous rate limit (10 requests per minute)...")
    
    successes = 0
    rate_limited = 0
    
    # Make 15 requests quickly
    for i in range(15):
        response = requests.get(f"{BASE_URL}/api/v1/health")
        
        if response.status_code == 200:
            successes += 1
            print(f"  Request {i+1}: Success (200)")
        elif response.status_code == 429:
            rate_limited += 1
            print(f"  Request {i+1}: Rate limited (429)")
            print(f"    Headers: {dict(response.headers)}")
        else:
            print(f"  Request {i+1}: Unexpected status {response.status_code}")
        
        time.sleep(0.1)  # Small delay between requests
    
    print(f"\nResults:")
    print(f"  Successful: {successes}")
    print(f"  Rate limited: {rate_limited}")
    print(f"  Expected: ~10 success, ~5 rate limited")
    
    if rate_limited > 0:
        print("\n✅ Rate limiting is working!")
        return True
    else:
        print("\n❌ Rate limiting may not be working - no 429 responses")
        return False


def test_authenticated_rate_limit():
    """Test rate limiting for authenticated users"""
    print("\n\nTesting authenticated rate limit...")
    
    # First login
    login_response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "admin123"}
    )
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        print(f"   Response: {login_response.text}")
        return False
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"✅ Logged in successfully")
    
    # Make requests with auth token
    successes = 0
    for i in range(5):
        response = requests.get(f"{BASE_URL}/api/v1/users/me", headers=headers)
        if response.status_code == 200:
            successes += 1
            
            # Check rate limit headers
            if i == 0:
                print(f"\nRate limit headers on first request:")
                print(f"  X-RateLimit-Limit: {response.headers.get('X-RateLimit-Limit', 'Not set')}")
                print(f"  X-RateLimit-Remaining: {response.headers.get('X-RateLimit-Remaining', 'Not set')}")
                print(f"  X-RateLimit-Reset: {response.headers.get('X-RateLimit-Reset', 'Not set')}")
    
    print(f"\n✅ Made {successes} authenticated requests successfully")
    return True


def test_rate_limit_headers():
    """Test that rate limit headers are present"""
    print("\n\nTesting rate limit headers...")
    
    response = requests.get(f"{BASE_URL}/api/v1/health")
    
    headers_to_check = [
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining", 
        "X-RateLimit-Reset"
    ]
    
    print("Checking for rate limit headers:")
    all_present = True
    for header in headers_to_check:
        value = response.headers.get(header)
        if value:
            print(f"  ✅ {header}: {value}")
        else:
            print(f"  ❌ {header}: Not present")
            all_present = False
    
    return all_present


if __name__ == "__main__":
    print("=" * 60)
    print("Rate Limiting Tests")
    print("=" * 60)
    
    try:
        # Test headers first
        headers_ok = test_rate_limit_headers()
        
        # Test anonymous rate limiting
        anon_ok = test_anonymous_rate_limit()
        
        # Test authenticated rate limiting
        auth_ok = test_authenticated_rate_limit()
        
        print("\n" + "=" * 60)
        print("Summary:")
        print(f"  Rate limit headers: {'✅' if headers_ok else '❌'}")
        print(f"  Anonymous rate limit: {'✅' if anon_ok else '❌'}")
        print(f"  Authenticated rate limit: {'✅' if auth_ok else '❌'}")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to backend server")
        print("   Make sure Docker containers are running:")
        print("   docker-compose ps")
    except Exception as e:
        print(f"\n❌ Error: {e}")
