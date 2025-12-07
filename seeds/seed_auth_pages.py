#!/usr/bin/env python3
"""
Seed Auth Pages Content
This script cleans up and seeds auth_page entries correctly.
"""

import json
import os
import sys
import time

import requests

# Configuration
CMS_URL = "http://localhost:8000"
EMAIL = "bsakweson@gmail.com"
PASSWORD = "Angelbenise1"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def get_token():
    """Get authentication token"""
    response = requests.post(
        f"{CMS_URL}/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        sys.exit(1)
    return response.json()["access_token"]


def delete_all_auth_pages(token):
    """Delete all existing auth_page entries"""
    headers = {"Authorization": f"Bearer {token}"}

    deleted_count = 0
    page = 1

    while True:
        # Get auth_page entries (paginated)
        response = requests.get(
            f"{CMS_URL}/api/v1/content/entries",
            params={"content_type_api_id": "auth_page", "page_size": 100, "page": page},
            headers=headers,
        )

        if response.status_code != 200:
            print(f"Failed to fetch entries: {response.text}")
            break

        data = response.json()
        entries = data.get("items", [])

        if not entries:
            break

        print(f"  Deleting batch of {len(entries)} entries...")

        for entry in entries:
            entry_id = entry["id"]
            del_response = requests.delete(
                f"{CMS_URL}/api/v1/content/entries/{entry_id}", headers=headers
            )
            if del_response.status_code in [200, 204]:
                deleted_count += 1
            else:
                print(f"    Failed to delete {entry_id}: {del_response.status_code}")
            time.sleep(0.05)  # Rate limit protection

        # If we deleted all items on this page, stay on page 1
        # Otherwise move to next page
        if len(entries) < 100:
            break

    print(f"  Deleted {deleted_count} entries total")


def get_content_type_id(token, api_id):
    """Get content type UUID by api_id"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{CMS_URL}/api/v1/content/types", params={"page_size": 50}, headers=headers
    )
    if response.status_code != 200:
        return None

    for ct in response.json():
        if ct["api_id"] == api_id:
            return ct["id"]
    return None


def create_auth_pages(token):
    """Create auth_page entries from seed data"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Get content type ID
    content_type_id = get_content_type_id(token, "auth_page")
    if not content_type_id:
        print("  ✗ Could not find auth_page content type")
        return
    print(f"  Using content_type_id: {content_type_id}")

    # Load seed data
    seed_file = os.path.join(SCRIPT_DIR, "sample-data/13-auth-pages.json")
    with open(seed_file, "r") as f:
        seed_data = json.load(f)

    entries = seed_data.get("entries", [])
    print(f"\nCreating {len(entries)} auth_page entries...")

    for entry in entries:
        slug = entry["slug"]
        data = entry["data"]

        # Build the entry payload with content_type_id and data nested
        payload = {
            "content_type_id": content_type_id,
            "slug": slug,
            "status": "published",
            "data": {
                "page_key": data.get("page_key"),
                "title": data.get("title"),
                "subtitle": data.get("subtitle"),
                "description": data.get("description"),
                "form_labels": data.get("form_labels"),
                "button_text": data.get("button_text"),
                "messages": data.get("messages"),
                "links": data.get("links"),
                "social_login": data.get("social_login"),
                "legal_text": data.get("legal_text"),
            },
        }

        # Remove None values from data
        payload["data"] = {k: v for k, v in payload["data"].items() if v is not None}

        response = requests.post(f"{CMS_URL}/api/v1/content/entries", json=payload, headers=headers)

        if response.status_code in [200, 201]:
            print(f"  ✓ Created: {slug}")
        else:
            print(f"  ✗ Failed to create {slug}: {response.status_code} - {response.text[:300]}")

        time.sleep(0.2)  # Rate limit protection


def main():
    print("=" * 50)
    print("Auth Pages Seeder")
    print("=" * 50)

    # Get token
    print("\n1. Authenticating...")
    token = get_token()
    print("   ✓ Authenticated")

    # Delete existing entries
    print("\n2. Cleaning up existing auth_page entries...")
    delete_all_auth_pages(token)

    # Create new entries
    print("\n3. Creating auth_page entries...")
    create_auth_pages(token)

    print("\n" + "=" * 50)
    print("Done!")
    print("=" * 50)


if __name__ == "__main__":
    main()
