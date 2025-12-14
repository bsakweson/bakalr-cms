#!/usr/bin/env python3
"""
Update Auth Page Content Type Schema
Adds new fields for the right panel: badge_text, subtext, benefits, trust_indicator
"""

import os
import sys

import requests

# Configuration
CMS_URL = os.getenv("CMS_URL", "http://localhost:8000")
EMAIL = os.getenv("CMS_EMAIL", "request username")
PASSWORD = os.getenv("CMS_PASSWORD", "request password")

# New fields to add
NEW_FIELDS = [
    {
        "name": "badge_text",
        "type": "text",
        "required": False,
        "localized": True,
        "help_text": "Badge text shown in the side panel (e.g., 'Secure Shopping Experience') - IS translated",
    },
    {
        "name": "subtext",
        "type": "textarea",
        "required": False,
        "localized": True,
        "help_text": "Subtext shown below the main description in side panel - IS translated",
    },
    {
        "name": "benefits",
        "type": "json",
        "required": False,
        "localized": True,
        "help_text": "Array of benefit strings shown in side panel - IS translated",
    },
    {
        "name": "trust_indicator",
        "type": "json",
        "required": False,
        "localized": True,
        "help_text": "Trust indicator config: {primary, secondary, count} - IS translated",
    },
]


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


def get_content_type(token, api_id):
    """Get content type by api_id"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{CMS_URL}/api/v1/content/types", params={"page_size": 50}, headers=headers
    )
    if response.status_code != 200:
        print(f"❌ Failed to fetch content types: {response.text}")
        return None

    for ct in response.json():
        if ct["api_id"] == api_id:
            return ct
    return None


def update_content_type(token, content_type_id, updated_fields):
    """Update content type with new fields"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.patch(
        f"{CMS_URL}/api/v1/content/types/{content_type_id}",
        json={"fields": updated_fields},
        headers=headers,
    )
    if response.status_code not in [200, 201]:
        print(f"❌ Failed to update content type: {response.text}")
        return None
    return response.json()


def main():
    print("\n" + "=" * 60)
    print("Update Auth Page Content Type Schema")
    print("=" * 60 + "\n")

    # Get token
    token = get_token()

    # Get current auth_page content type
    print("\n→ Fetching auth_page content type...")
    content_type = get_content_type(token, "auth_page")

    if not content_type:
        print("❌ auth_page content type not found!")
        sys.exit(1)

    print(f"✓ Found auth_page (id: {content_type['id']})")

    # Get current fields
    current_fields = content_type.get("fields", [])
    current_field_names = {f["name"] for f in current_fields}

    print(f"  Current fields: {len(current_fields)}")
    for f in current_fields:
        print(f"    - {f['name']} ({f['type']})")

    # Check which new fields need to be added
    fields_to_add = []
    for field in NEW_FIELDS:
        if field["name"] not in current_field_names:
            fields_to_add.append(field)
            print(f"\n  + Will add: {field['name']} ({field['type']})")
        else:
            print(f"\n  ~ Already exists: {field['name']}")

    if not fields_to_add:
        print("\n✓ All fields already exist. Nothing to update.")
        return

    # Merge fields
    updated_fields = current_fields + fields_to_add

    print(f"\n→ Updating content type with {len(fields_to_add)} new fields...")
    result = update_content_type(token, content_type["id"], updated_fields)

    if result:
        print("✓ Content type updated successfully!")
        print(f"\n  New total fields: {len(result.get('fields', []))}")
    else:
        print("❌ Failed to update content type")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Done! Now update the auth_page entries with the new field values.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
