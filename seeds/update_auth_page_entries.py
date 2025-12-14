#!/usr/bin/env python3
"""
Update Auth Page Entries with New Fields
Adds badge_text, subtext, benefits, and trust_indicator to login and register pages
"""

import os
import sys
import time

import requests

# Configuration
CMS_URL = os.getenv("CMS_URL", "http://localhost:8000")
EMAIL = os.getenv("CMS_EMAIL", "request userid")
PASSWORD = os.getenv("CMS_PASSWORD", "request for passord")

# New field values for each page
PAGE_UPDATES = {
    "login": {
        "badge_text": "Secure Shopping Experience",
        "subtext": "View orders, manage your profile, and enjoy a personalized shopping experience.",
        "benefits": [
            "Access exclusive deals and offers",
            "Track your orders in real-time",
            "Save your favorites for later",
        ],
        "trust_indicator": {
            "primary": "Trusted by 10,000+ shoppers",
            "secondary": "Join our growing community",
            "count": 4,
        },
    },
    "register": {
        "badge_text": "Secure Shopping Experience",
        "subtext": "Create your account to unlock all features and start your personalized shopping journey.",
        "benefits": [
            "Free shipping on orders over $50",
            "Early access to new collections",
            "Exclusive member-only discounts",
            "Birthday rewards and special offers",
        ],
        "trust_indicator": {
            "primary": "Trusted by 10,000+ shoppers",
            "secondary": "Join our growing community",
            "count": 4,
        },
    },
}


def get_token():
    """Get authentication token"""
    response = requests.post(
        f"{CMS_URL}/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    if response.status_code != 200:
        print(f"❌ Login failed: {response.text}")
        sys.exit(1)
    print("✓ Logged in successfully")
    return response.json()["access_token"]


def get_auth_page_entry(token, page_key):
    """Get auth_page entry by page_key"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{CMS_URL}/api/v1/content/entries",
        params={"content_type_api_id": "auth_page", "page_size": 100},
        headers=headers,
    )
    if response.status_code != 200:
        print(f"❌ Failed to fetch entries: {response.text}")
        return None

    data = response.json()
    entries = data.get("items", [])

    for entry in entries:
        entry_data = entry.get("data") or entry.get("fields", {})
        if entry_data.get("page_key") == page_key:
            return entry
    return None


def update_entry(token, entry_id, new_data):
    """Update entry with new field values"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.patch(
        f"{CMS_URL}/api/v1/content/entries/{entry_id}", json={"data": new_data}, headers=headers
    )
    if response.status_code not in [200, 201]:
        print(f"❌ Failed to update entry: {response.text}")
        return None
    return response.json()


def main():
    print("\n" + "=" * 60)
    print("Update Auth Page Entries with New Fields")
    print("=" * 60 + "\n")

    # Get token
    token = get_token()

    # Update each page
    for page_key, new_fields in PAGE_UPDATES.items():
        print(f"\n→ Updating {page_key} page...")

        # Get current entry
        entry = get_auth_page_entry(token, page_key)
        if not entry:
            print(f"  ❌ Entry not found for page_key: {page_key}")
            continue

        print(f"  ✓ Found entry (id: {entry['id']}, slug: {entry.get('slug')})")

        # Get current data
        current_data = entry.get("data") or entry.get("fields", {})

        # Merge new fields into existing data
        updated_data = {**current_data, **new_fields}

        # Update the entry
        result = update_entry(token, entry["id"], updated_data)

        if result:
            print(f"  ✓ Updated {page_key} with:")
            print(f"    - badge_text: {new_fields['badge_text']}")
            print(f"    - subtext: {new_fields['subtext'][:50]}...")
            print(f"    - benefits: {len(new_fields['benefits'])} items")
            print(f"    - trust_indicator: {new_fields['trust_indicator']['primary']}")
        else:
            print(f"  ❌ Failed to update {page_key}")

        time.sleep(0.1)  # Small delay between updates

    print("\n" + "=" * 60)
    print("Done! Auth pages now have the new CMS-driven fields.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
