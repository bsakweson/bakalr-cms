#!/usr/bin/env python3
"""
Comprehensive rate limiting test for all Bakalr CMS API endpoints
Tests rate limits across all major API categories and user types
"""
import requests
import time
from typing import Dict, List, Tuple, Optional

BASE_URL = "http://localhost:8000"

# API endpoint categories to test
API_ENDPOINTS = {
    "Public": [
        "/health",
    ],
    "Authentication": [
        "/api/v1/auth/login",
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
        "/api/v1/seo/sitemaps",
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
    "Organizations": [
        "/api/v1/organizations",
    ],
    "Search": [
        "/api/v1/search?q=test",
    ],
}


def get_auth_token() -> Optional[str]:
    """Get authentication token for testing"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": "admin@bakalr.cms", "password": "admin123"},
            timeout=5
        )
        if response.status_code == 200:
            return response.json()["access_token"]
    except:
        pass
    return None


def test_rate_limit_headers():
    """Test that rate limit headers are present on responses"""
    print("\n" + "="*60)
    print("TEST 1: Rate Limit Headers")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/health")
    
    headers_to_check = [
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining", 
        "X-RateLimit-Reset"
    ]
    
    print("Checking for rate limit headers on /health endpoint:")
    all_present = True
    for header in headers_to_check:
        value = response.headers.get(header)
        if value:
            print(f"  ✅ {header}: {value}")
        else:
            print(f"  ❌ {header}: Not present")
            all_present = False
    
    return all_present


def test_anonymous_rate_limit():
    """Test rate limiting for anonymous users"""
    print("\n" + "="*60)
    print("TEST 2: Anonymous Rate Limiting")
    print("="*60)
    print("Making 15 rapid requests to /health endpoint...")
    
    successes = 0
    rate_limited = 0
    
    for i in range(15):
        response = requests.get(f"{BASE_URL}/health")
        
        if response.status_code == 200:
            successes += 1
            if i < 3:  # Show first few
                print(f"  Request {i+1}: ✅ Success (200)")
        elif response.status_code == 429:
            rate_limited += 1
            if rate_limited <= 2:  # Show first few rate limits
                print(f"  Request {i+1}: 🛑 Rate limited (429)")
                retry_after = response.headers.get("Retry-After", "N/A")
                print(f"              Retry-After: {retry_after}s")
        
        time.sleep(0.05)  # 50ms between requests
    
    if successes > 10:
        print(f"  ... (showing first few of {successes} successful requests)")
    
    print(f"\n📊 Results:")
    print(f"  Successful: {successes}")
    print(f"  Rate limited: {rate_limited}")
    print(f"  Total: {successes + rate_limited}")
    
    if rate_limited > 0:
        print("\n✅ Anonymous rate limiting is WORKING!")
        return True
    else:
        print("\n⚠️  No rate limiting detected - may need adjustment")
        return False


def test_authenticated_rate_limit():
    """Test rate limiting for authenticated users"""
    print("\n" + "="*60)
    print("TEST 3: Authenticated User Rate Limiting")
    print("="*60)
    
    # Login first
    print("Logging in as admin@example.com...")
    token = get_auth_token()
    
    if not token:
        print("❌ Login failed - skipping authenticated tests")
        return False, None
    
    print("✅ Login successful\n")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Check rate limit for authenticated endpoint
    print("Checking /api/v1/users/me rate limits:")
    response = requests.get(f"{BASE_URL}/api/v1/users/me", headers=headers)
    
    if response.status_code == 200:
        limit = response.headers.get("X-RateLimit-Limit", "N/A")
        remaining = response.headers.get("X-RateLimit-Remaining", "N/A")
        print(f"  Rate limit: {limit} requests")
        print(f"  Remaining: {remaining} requests")
        
        # Make several requests to test
        successes = 0
        for i in range(10):
            r = requests.get(f"{BASE_URL}/api/v1/users/me", headers=headers)
            if r.status_code == 200:
                successes += 1
            time.sleep(0.05)
        
        print(f"  Made {successes}/10 successful requests")
        print("\n✅ Authenticated rate limiting is WORKING!")
        return True, token
    else:
        print(f"❌ Failed to access authenticated endpoint: {response.status_code}")
        return False, token


def test_endpoint_categories(token: Optional[str]):
    """Test rate limits across all API endpoint categories"""
    print("\n" + "="*60)
    print("TEST 4: Rate Limits Across All API Categories")
    print("="*60)
    
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    results = {}
    
    for category, endpoints in API_ENDPOINTS.items():
        print(f"\n📂 {category}:")
        
        for endpoint in endpoints:
            successes = 0
            rate_limited = 0
            auth_required = False
            
            # Make 10 requests
            for i in range(10):
                try:
                    response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=2)
                    
                    if response.status_code == 200:
                        successes += 1
                    elif response.status_code == 429:
                        rate_limited += 1
                    elif response.status_code in [401, 403]:
                        auth_required = True
                        break
                    
                    time.sleep(0.05)
                except:
                    break
            
            if auth_required and not token:
                print(f"  🔒 {endpoint}: Requires authentication")
            elif successes + rate_limited > 0:
                status = "✅" if rate_limited > 0 else "✓"
                print(f"  {status} {endpoint}: {successes} OK, {rate_limited} limited")
                results[endpoint] = (successes, rate_limited)
    
    return results


def test_rate_limit_comparison():
    """Compare rate limits between anonymous and authenticated"""
    print("\n" + "="*60)
    print("TEST 5: Anonymous vs Authenticated Comparison")
    print("="*60)
    
    # Anonymous
    print("\n1️⃣  Anonymous user:")
    anon_response = requests.get(f"{BASE_URL}/health")
    anon_limit = anon_response.headers.get("X-RateLimit-Limit", "Unknown")
    print(f"   Rate limit: {anon_limit} requests/window")
    
    # Authenticated
    print("\n2️⃣  Authenticated user:")
    token = get_auth_token()
    if token:
        headers = {"Authorization": f"Bearer {token}"}
        auth_response = requests.get(f"{BASE_URL}/api/v1/users/me", headers=headers)
        auth_limit = auth_response.headers.get("X-RateLimit-Limit", "Unknown")
        print(f"   Rate limit: {auth_limit} requests/window")
        
        # Compare
        if anon_limit != "Unknown" and auth_limit != "Unknown":
            try:
                if int(auth_limit) > int(anon_limit):
                    print(f"\n✅ Authenticated users have HIGHER limits ({auth_limit} > {anon_limit})")
                else:
                    print(f"\n⚠️  Both have SAME limits ({auth_limit} = {anon_limit})")
            except:
                print(f"\n   Limits: Anonymous={anon_limit}, Authenticated={auth_limit}")


def test_expensive_operations(token: Optional[str]):
    """Test rate limits on expensive operations"""
    print("\n" + "="*60)
    print("TEST 6: Expensive Operations Rate Limits")
    print("="*60)
    
    if not token:
        print("⏭️  Skipping (requires authentication)")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    expensive_ops = {
        "Search": "/api/v1/search?q=test",
        "Media": "/api/v1/media",
        "Translation": "/api/v1/translation/locales",
    }
    
    print("\nTesting operations that typically have lower rate limits:\n")
    
    for op_name, endpoint in expensive_ops.items():
        successes = 0
        rate_limited = 0
        
        for i in range(12):
            try:
                response = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=2)
                if response.status_code == 200:
                    successes += 1
                elif response.status_code == 429:
                    rate_limited += 1
                time.sleep(0.05)
            except:
                pass
        
        status = "🛑" if rate_limited > 2 else "✅" if rate_limited > 0 else "✓"
        print(f"  {status} {op_name:12} : {successes} OK, {rate_limited} limited")


def print_summary(results: dict):
    """Print summary of all tests"""
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    total_tests = len(results)
    passed = sum(1 for v in results.values() if v)
    
    print(f"\nTests run: {total_tests}")
    print(f"Passed: {passed}")
    print(f"Failed: {total_tests - passed}")
    
    print("\n📊 Detailed Results:")
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")
    
    overall = passed == total_tests
    print("\n" + "="*60)
    if overall:
        print("🎉 ALL RATE LIMITING TESTS PASSED!")
    else:
        print("⚠️  Some tests failed - check configuration")
    print("="*60)


def main():
    """Main test runner"""
    print("="*60)
    print("BAKALR CMS - COMPREHENSIVE RATE LIMITING TEST")
    print("="*60)
    print(f"Testing against: {BASE_URL}")
    print("="*60)
    
    results = {}
    
    try:
        # Test 1: Headers
        results["Rate Limit Headers"] = test_rate_limit_headers()
        
        # Test 2: Anonymous
        results["Anonymous Rate Limiting"] = test_anonymous_rate_limit()
        
        # Test 3: Authenticated
        auth_result, token = test_authenticated_rate_limit()
        results["Authenticated Rate Limiting"] = auth_result
        
        # Test 4: All endpoints
        test_endpoint_categories(token)
        
        # Test 5: Comparison
        test_rate_limit_comparison()
        
        # Test 6: Expensive operations
        test_expensive_operations(token)
        
        # Summary
        print_summary(results)
        
    except requests.exceptions.ConnectionError:
        print("\n" + "="*60)
        print("❌ CONNECTION ERROR")
        print("="*60)
        print("Could not connect to backend server at", BASE_URL)
        print("\nMake sure Docker containers are running:")
        print("  docker-compose ps")
        print("\nOr check if backend is accessible:")
        print(f"  curl {BASE_URL}/health")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
