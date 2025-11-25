"""
Translation API Test Script
Tests locale management and auto-translation functionality
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000/api/v1"

def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def print_response(response):
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text}")

# Setup
print("🔵 Setting up authentication...")
register_data = {
    "email": "translation_test@example.com",
    "password": "TestPassword123!",
    "first_name": "Translation",
    "last_name": "Tester"
}
response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
if response.status_code == 201:
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Authenticated successfully")
else:
    # Try login
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "email": register_data["email"],
        "password": register_data["password"]
    })
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Logged in successfully")

# Test 1: Create locales
print("\n🔵 Creating locales...")

print_section("CREATE ENGLISH LOCALE (DEFAULT)")
locale_en = {
    "code": "en",
    "name": "English",
    "native_name": "English",
    "is_default": True,
    "is_enabled": True,
    "auto_translate": False  # Don't auto-translate English
}
response = requests.post(f"{BASE_URL}/translation/locales", json=locale_en, headers=headers)
print_response(response)
if response.status_code == 201:
    locale_en_id = response.json()["id"]
    print(f"✅ English locale created with ID: {locale_en_id}")

print_section("CREATE SPANISH LOCALE")
locale_es = {
    "code": "es",
    "name": "Spanish",
    "native_name": "Español",
    "is_default": False,
    "is_enabled": True,
    "auto_translate": True
}
response = requests.post(f"{BASE_URL}/translation/locales", json=locale_es, headers=headers)
print_response(response)
if response.status_code == 201:
    locale_es_id = response.json()["id"]
    print(f"✅ Spanish locale created with ID: {locale_es_id}")

print_section("CREATE FRENCH LOCALE")
locale_fr = {
    "code": "fr",
    "name": "French",
    "native_name": "Français",
    "is_default": False,
    "is_enabled": True,
    "auto_translate": True
}
response = requests.post(f"{BASE_URL}/translation/locales", json=locale_fr, headers=headers)
print_response(response)
if response.status_code == 201:
    locale_fr_id = response.json()["id"]
    print(f"✅ French locale created with ID: {locale_fr_id}")

# Test 2: List locales
print("\n🔵 Listing all locales...")
print_section("LIST LOCALES")
response = requests.get(f"{BASE_URL}/translation/locales", headers=headers)
print_response(response)

# Test 3: Create content type
print("\n🔵 Creating content type...")
content_type_data = {
    "name": "Article",
    "api_id": "article",
    "description": "News article content type",
    "fields": [
        {
            "name": "title",
            "type": "text",
            "required": True,
            "localized": True,
            "help_text": "Article title"
        },
        {
            "name": "body",
            "type": "textarea",
            "required": True,
            "localized": True,
            "help_text": "Article body content"
        },
        {
            "name": "author",
            "type": "text",
            "required": False,
            "localized": False
        }
    ]
}
response = requests.post(f"{BASE_URL}/content/types", json=content_type_data, headers=headers)
if response.status_code == 201:
    content_type_id = response.json()["id"]
    print(f"✅ Content type created with ID: {content_type_id}")

# Test 4: Create content entry (should auto-translate)
print("\n🔵 Creating content entry with auto-translation...")
print_section("CREATE CONTENT ENTRY")
entry_data = {
    "content_type_id": content_type_id,
    "data": {
        "title": "Hello World",
        "body": "This is a test article about artificial intelligence and machine learning.",
        "author": "Test Author"
    },
    "slug": "hello-world",
    "status": "draft"
}
response = requests.post(f"{BASE_URL}/content/entries", json=entry_data, headers=headers)
print_response(response)
if response.status_code == 201:
    entry_id = response.json()["id"]
    print(f"✅ Content entry created with ID: {entry_id}")
    print("⏳ Auto-translation triggered in background...")

# Wait a bit for translation
import time
print("\n⏱️  Waiting 5 seconds for auto-translation to complete...")
time.sleep(5)

# Test 5: Check translations
print("\n🔵 Checking auto-generated translations...")
print_section("LIST TRANSLATIONS FOR ENTRY")
response = requests.get(f"{BASE_URL}/translation/translations?content_entry_id={entry_id}", headers=headers)
print_response(response)
if response.status_code == 200:
    translations = response.json()["items"]
    print(f"\n✅ Found {len(translations)} translation(s)")
    for t in translations:
        print(f"   - Locale ID {t['locale_id']}: {t['status']} ({t['translation_service']})")

# Test 6: Manual translation
print("\n🔵 Testing manual translation...")
print_section("TRANSLATE TO SPECIFIC LOCALES")
translate_request = {
    "content_entry_id": entry_id,
    "target_locale_ids": [locale_es_id, locale_fr_id],
    "force_retranslate": True
}
response = requests.post(f"{BASE_URL}/translation/translate", json=translate_request, headers=headers)
print_response(response)
if response.status_code == 200:
    print("✅ Manual translation queued")

# Wait for manual translation
print("\n⏱️  Waiting 5 seconds for manual translation...")
time.sleep(5)

# Check translations again
print("\n🔵 Checking translations after manual trigger...")
print_section("LIST ALL TRANSLATIONS")
response = requests.get(f"{BASE_URL}/translation/translations?content_entry_id={entry_id}", headers=headers)
print_response(response)

# Test 7: Language detection
print("\n🔵 Testing language detection...")
print_section("DETECT LANGUAGE")
response = requests.post(
    f"{BASE_URL}/translation/detect-locale?text=Bonjour, comment allez-vous?",
    headers=headers
)
print_response(response)

print("\n" + "="*60)
print("  🎉 All translation tests completed!")
print("="*60)
