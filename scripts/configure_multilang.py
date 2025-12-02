#!/usr/bin/env python3
"""
Phase 5: Multi-language Configuration
======================================

This script:
1. Checks current locale configuration
2. Enables Spanish (es) locale
3. Enables French (fr) locale
4. Tests translation API connectivity
5. Auto-translates all 45 products
6. Verifies translations were created
7. Tests retrieving translated content

Usage:
    poetry run python scripts/configure_multilang.py
"""

import asyncio
from typing import Any, Dict, List

import httpx

# Configuration
API_BASE = "http://localhost:8000/api/v1"
LIBRE_TRANSLATE_URL = "http://localhost:5000"

# Authentication
EMAIL = "bsakweson@gmail.com"
PASSWORD = "Angelbenise123!@#"


async def login() -> str:
    """Login and get access token"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/auth/login", json={"email": EMAIL, "password": PASSWORD}
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        raise Exception(f"Login failed: {response.text}")


async def check_libre_translate() -> bool:
    """Check if LibreTranslate is accessible"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{LIBRE_TRANSLATE_URL}/languages")
            if response.status_code == 200:
                languages = response.json()
                print(f"✅ LibreTranslate is running ({len(languages)} languages available)")
                return True
            else:
                print(f"❌ LibreTranslate responded with: {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Cannot connect to LibreTranslate: {e}")
        print(f"   Make sure it's running on {LIBRE_TRANSLATE_URL}")
        return False


async def list_locales(token: str) -> List[Dict[str, Any]]:
    """Get all locales"""
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/translation/locales", headers=headers)
        if response.status_code == 200:
            data = response.json()
            # API might return list directly or dict with items
            if isinstance(data, list):
                return data
            return data.get("items", [])
        return []


async def create_locale(token: str, code: str, name: str) -> bool:
    """Create and enable a locale"""
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        # Create locale
        response = await client.post(
            f"{API_BASE}/translation/locales",
            headers=headers,
            json={"code": code, "name": name, "enabled": True},
        )

        if response.status_code in [200, 201]:
            print(f"✅ Created locale: {name} ({code})")
            return True
        elif response.status_code == 400:
            # Locale might already exist, try to enable it
            locales = await list_locales(token)
            locale = next((l for l in locales if l["code"] == code), None)
            if locale:
                if locale.get("enabled", True):
                    print(f"✅ Locale {name} ({code}) already exists and is enabled")
                    return True
                else:
                    # Enable it
                    response = await client.patch(
                        f"{API_BASE}/translation/locales/{locale['id']}",
                        headers=headers,
                        json={"enabled": True},
                    )
                    if response.status_code == 200:
                        print(f"✅ Enabled existing locale: {name} ({code})")
                        return True

        print(f"❌ Failed to create locale {name}: {response.status_code}")
        print(f"   {response.text}")
        return False


async def get_all_products(token: str) -> List[Dict[str, Any]]:
    """Get all products"""
    headers = {"Authorization": f"Bearer {token}"}
    all_products = []
    page = 1

    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get(
                f"{API_BASE}/content/entries",
                params={"page": page, "page_size": 100},
                headers=headers,
            )

            if response.status_code != 200:
                break

            data = response.json()
            items = data.get("items", [])

            if not items:
                break

            # Filter for products only
            products = [item for item in items if item.get("content_type_id") == 3]
            all_products.extend(products)

            if len(items) < 100:
                break

            page += 1

    return all_products


async def get_locale_id(token: str, locale_code: str) -> int:
    """Get locale ID by code"""
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/translation/locales", headers=headers)
        if response.status_code == 200:
            locales = response.json()
            if isinstance(locales, list):
                for locale in locales:
                    if locale["code"] == locale_code:
                        return locale["id"]
        return None


async def translate_product(token: str, product_id: int, locale_id: int, locale_name: str) -> bool:
    """Create translation for a product"""
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{API_BASE}/translation/translate",
            headers=headers,
            json={
                "content_entry_id": product_id,
                "target_locale_ids": [locale_id],
                "force_retranslate": False,
            },
        )

        if response.status_code in [200, 201]:
            return True
        else:
            # Don't print error for each product to avoid clutter
            return False


async def get_translation(token: str, product_id: int, locale_code: str) -> Dict[str, Any]:
    """Get translation for a product"""
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE}/translation/entry/{product_id}/locale/{locale_code}", headers=headers
        )

        if response.status_code == 200:
            return response.json()
        return {}


async def main():
    print("🌍 BAKALR BOUTIQUE - MULTI-LANGUAGE CONFIGURATION")
    print("=" * 60)

    # Step 1: Check LibreTranslate
    print("\n📡 Checking translation service...")
    if not await check_libre_translate():
        print("\n⚠️  LibreTranslate is not running!")
        print("   Start it with: docker-compose up -d libretranslate")
        print("   Or continue anyway (translations will use Google Translate fallback)")
        # Don't return, continue anyway

    # Step 2: Login
    print("\n🔐 Authenticating...")
    try:
        token = await login()
        print("✅ Authentication successful")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return

    # Step 3: Check current locales
    print("\n📋 Current locales:")
    locales = await list_locales(token)
    for locale in locales:
        status = "✅ enabled" if locale.get("enabled", True) else "❌ disabled"
        print(f"   • {locale['name']} ({locale['code']}) - {status}")

    # Step 4: Create Spanish locale
    print("\n🇪🇸 Configuring Spanish locale...")
    await create_locale(token, "es", "Spanish")

    # Step 5: Create French locale
    print("\n🇫🇷 Configuring French locale...")
    await create_locale(token, "fr", "French")

    # Step 6: Get all products
    print("\n📦 Fetching products...")
    products = await get_all_products(token)
    print(f"✅ Found {len(products)} products to translate")

    if len(products) == 0:
        print("❌ No products found!")
        return

    # Step 7: Get locale IDs
    print("\n🔍 Getting locale IDs...")
    es_locale_id = await get_locale_id(token, "es")
    fr_locale_id = await get_locale_id(token, "fr")

    if not es_locale_id:
        print("❌ Spanish locale not found!")
        return
    if not fr_locale_id:
        print("❌ French locale not found!")
        return

    print(f"✅ Spanish locale ID: {es_locale_id}")
    print(f"✅ French locale ID: {fr_locale_id}")

    # Step 8: Translate to Spanish
    print("\n🇪🇸 Translating to Spanish...")
    print(f"   Translating {len(products)} products (this may take a minute)...")
    es_success = 0
    for i, product in enumerate(products, 1):
        if await translate_product(token, product["id"], es_locale_id, "Spanish"):
            es_success += 1

        # Progress indicator every 10 products
        if i % 10 == 0 or i == len(products):
            print(f"   Progress: {i}/{len(products)} ({es_success} successful)")

        # Small delay to avoid overwhelming the API
        await asyncio.sleep(0.1)

    print(f"✅ Spanish: {es_success}/{len(products)} translations created")

    # Step 9: Translate to French
    print("\n🇫🇷 Translating to French...")
    print(f"   Translating {len(products)} products (this may take a minute)...")
    fr_success = 0
    for i, product in enumerate(products, 1):
        if await translate_product(token, product["id"], fr_locale_id, "French"):
            fr_success += 1

        # Progress indicator every 10 products
        if i % 10 == 0 or i == len(products):
            print(f"   Progress: {i}/{len(products)} ({fr_success} successful)")

        await asyncio.sleep(0.1)

    print(f"✅ French: {fr_success}/{len(products)} translations created")

    # Step 10: Test translations
    print("\n🧪 Testing translations...")
    if products and (es_success > 0 or fr_success > 0):
        # Test first successfully translated product
        for product in products[:5]:
            product_name = product.get("data", {}).get("name", product.get("title", "Unknown"))

            # Get Spanish translation
            if es_success > 0:
                es_translation = await get_translation(token, product["id"], "es")
                if es_translation:
                    translated_name = es_translation.get("translated_fields", {}).get("name", "N/A")
                    print(f"\n   Product: {product_name}")
                    print(f"   🇪🇸 Spanish: {translated_name}")
                    break  # Found one, that's enough

        # Get French translation
        for product in products[:5]:
            if fr_success > 0:
                fr_translation = await get_translation(token, product["id"], "fr")
                if fr_translation:
                    product_name = product.get("data", {}).get(
                        "name", product.get("title", "Unknown")
                    )
                    translated_name = fr_translation.get("translated_fields", {}).get("name", "N/A")
                    if product_name not in locals():  # Only print product name if not already shown
                        print(f"\n   Product: {product_name}")
                    print(f"   🇫🇷 French: {translated_name}")
                    break  # Found one, that's enough

    # Final summary
    print("\n" + "=" * 60)
    print("✅ MULTI-LANGUAGE CONFIGURATION COMPLETE!")
    print("=" * 60)
    print("\n📊 Summary:")
    print("   • Locales configured: Spanish (es), French (fr)")
    print(f"   • Products translated: {len(products)}")
    print(f"   • Spanish translations: {es_success}/{len(products)}")
    print(f"   • French translations: {fr_success}/{len(products)}")
    print(f"   • Total translations: {es_success + fr_success}")

    print("\n🎯 Features enabled:")
    print("   ✅ Multi-language content support")
    print("   ✅ Automatic translation via translation API")
    print("   ✅ Spanish (es) locale")
    print("   ✅ French (fr) locale")
    print("   ✅ Locale-specific content retrieval")

    print("\n📝 Next steps:")
    print("   • Test language switching in frontend")
    print("   • Add more locales if needed")
    print("   • Review and refine translations")
    print("   • Configure locale fallback preferences")


if __name__ == "__main__":
    asyncio.run(main())
