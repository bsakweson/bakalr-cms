#!/usr/bin/env python3
"""
Translate ALL content entries that are missing translations.
This script finds all entries without translations and triggers auto-translation.
"""

import time

import httpx

API_URL = "http://localhost:8000/api/v1"
API_KEY = "bk_p4mPH5PGxFb9yk3jd9O12ChtBcCt8fGfDlagg70tobI"

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# Target locales (fr, de, es)
TARGET_LOCALES = [
    "8f36bfaa-ef7f-482a-ade0-8932044ec4a5",  # French
    "2e87ede3-3b54-4690-ab93-70ca567d6d75",  # German
    "3c424c7b-6a9e-48ac-b66a-e8972087b9ae",  # Spanish
]


def get_all_entries():
    """Get all content entries"""
    entries = []
    page = 1

    while True:
        response = httpx.get(
            f"{API_URL}/content/entries",
            params={"page": page, "page_size": 100},
            headers=HEADERS,
            timeout=30.0,
        )
        data = response.json()
        entries.extend(data.get("items", []))

        if page >= data.get("pages", 1):
            break
        page += 1

    return entries


def check_translation_exists(entry_id: str, locale_code: str) -> bool:
    """Check if a translation exists for an entry"""
    try:
        response = httpx.get(
            f"{API_URL}/translation/translations/by-entry/{entry_id}",
            params={"locale_code": locale_code},
            headers=HEADERS,
            timeout=10.0,
        )
        return response.status_code == 200
    except:
        return False


def trigger_translation(entry_id: str, locale_ids: list) -> bool:
    """Trigger translation for an entry"""
    try:
        response = httpx.post(
            f"{API_URL}/translation/translate",
            json={
                "content_entry_id": entry_id,
                "target_locale_ids": locale_ids,
                "force_retranslate": False,
            },
            headers=HEADERS,
            timeout=120.0,
        )
        return response.status_code == 200
    except Exception as e:
        print(f"  Error: {e}")
        return False


def main():
    print("Fetching all content entries...")
    entries = get_all_entries()
    print(f"Found {len(entries)} entries\n")

    # Check each entry for missing translations
    missing = []

    print("Checking for missing translations...")
    for entry in entries:
        entry_id = entry["id"]
        slug = entry.get("slug", "unknown")
        content_type = entry.get("content_type", {}).get("api_id", "unknown")

        # Check each locale
        needs_translation = []
        for locale_id in TARGET_LOCALES:
            locale_code = {
                "8f36bfaa-ef7f-482a-ade0-8932044ec4a5": "fr",
                "2e87ede3-3b54-4690-ab93-70ca567d6d75": "de",
                "3c424c7b-6a9e-48ac-b66a-e8972087b9ae": "es",
            }.get(locale_id, "??")

            if not check_translation_exists(entry_id, locale_code):
                needs_translation.append(locale_id)

        if needs_translation:
            missing.append(
                {
                    "id": entry_id,
                    "slug": slug,
                    "type": content_type,
                    "missing_locales": needs_translation,
                }
            )
            print(f"  Missing: {content_type}/{slug} - {len(needs_translation)} locale(s)")

    print(f"\nFound {len(missing)} entries with missing translations\n")

    if not missing:
        print("All entries have translations!")
        return

    # Ask for confirmation
    response = input(f"Translate {len(missing)} entries? (y/n): ")
    if response.lower() != "y":
        print("Aborted")
        return

    # Trigger translations
    success = 0
    failed = 0

    for i, entry in enumerate(missing, 1):
        print(f"[{i}/{len(missing)}] Translating {entry['type']}/{entry['slug']}...", end=" ")

        if trigger_translation(entry["id"], entry["missing_locales"]):
            print("✓ queued")
            success += 1
        else:
            print("✗ failed")
            failed += 1

        # Small delay to not overwhelm the API
        time.sleep(0.5)

    print(f"\nDone! Success: {success}, Failed: {failed}")
    print("\nNote: Translations run in background. Wait a few seconds then refresh your page.")


if __name__ == "__main__":
    main()
