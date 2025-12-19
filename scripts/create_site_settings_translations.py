#!/usr/bin/env python3
"""
Create site_settings translations for all locales if they don't exist,
then auto-translate all common_labels.

Run inside Docker:
  docker cp scripts/create_site_settings_translations.py bakalr-backend:/app/ && \
  docker exec bakalr-backend python /app/create_site_settings_translations.py
"""

import json

from backend.core.translation_service import TranslationService
from backend.db.session import SessionLocal
from backend.models.content import ContentEntry
from backend.models.translation import Locale, Translation

SITE_SETTINGS_ID = "34850f0b-d781-4adf-94be-453461f5227e"


def deep_translate(
    data: dict, trans_service: TranslationService, locale: str, depth: int = 0
) -> dict:
    """Recursively translate all string values in a dict."""
    result = {}
    indent = "  " * depth

    # Fields that should never be translated (technical/ID fields)
    skip_keys = {
        "id",
        "key",
        "slug",
        "code",
        "icon",
        "color",
        "href",
        "url",
        "src",
        "path",
        "route",
        "name",
        "category",
    }

    # Brand names that should never be translated
    brand_names = {
        "stripe",
        "paypal",
        "m-pesa",
        "mpesa",
        "mtn mobile money",
        "mtn momo",
        "airtel money",
        "orange money",
        "wave",
        "flutterwave",
        "paystack",
        "apple pay",
        "google pay",
        "bitcoin",
        "klarna",
        "afterpay",
        "clearpay",
        "visa",
        "mastercard",
        "amex",
        "american express",
    }

    for key, value in data.items():
        # Skip technical fields and name field (usually brand names for payment methods)
        if key.lower() in skip_keys:
            result[key] = value
            continue

        if isinstance(value, str):
            try:
                # Skip URLs, paths, and brand names
                if value.startswith(("http://", "https://", "/", "#", "mailto:", "tel:")):
                    result[key] = value
                elif value.lower() in brand_names:
                    result[key] = value  # Keep brand names as-is
                else:
                    translation = trans_service.translate_text(
                        text=value, target_lang=locale, source_lang="en"
                    )
                    result[key] = translation.get("translated_text", value)
                    if depth < 3:  # Only print first few levels
                        print(f"{indent}  ✓ {key}: {value[:30]}... → {result[key][:30]}...")
            except Exception as e:
                print(f"{indent}  ✗ {key}: {e}")
                result[key] = value
        elif isinstance(value, dict):
            if depth < 4:
                print(f"{indent}  {key}:")
            result[key] = deep_translate(value, trans_service, locale, depth + 1)
        elif isinstance(value, list):
            # Recursively translate arrays of objects (e.g., payment_methods)
            translated_list = []
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    if depth < 2:
                        print(f"{indent}  {key}[{i}]:")
                    translated_list.append(deep_translate(item, trans_service, locale, depth + 1))
                elif isinstance(item, str) and not item.startswith(("http://", "https://", "/")):
                    try:
                        translation = trans_service.translate_text(
                            text=item, target_lang=locale, source_lang="en"
                        )
                        translated_list.append(translation.get("translated_text", item))
                    except:
                        translated_list.append(item)
                else:
                    translated_list.append(item)
            result[key] = translated_list
        else:
            result[key] = value  # Keep non-strings as-is (numbers, booleans, etc.)

    return result


def main():
    db = SessionLocal()
    translation_service = TranslationService()

    try:
        # Get site settings entry
        entry = db.query(ContentEntry).filter(ContentEntry.id == SITE_SETTINGS_ID).first()

        if not entry:
            print(f"❌ Site settings entry not found: {SITE_SETTINGS_ID}")
            return

        print(f"Found site settings: {entry.slug}")

        # Parse base data
        base_data = json.loads(entry.data) if isinstance(entry.data, str) else entry.data
        common_labels = base_data.get("common_labels", {})

        print(f"Common labels groups: {list(common_labels.keys())}")

        # Get all enabled locales
        locales = db.query(Locale).filter(Locale.is_enabled == True).all()
        print(f"Enabled locales: {[l.code for l in locales]}")

        for locale_obj in locales:
            if locale_obj.code == "en":
                continue  # Skip English (it's the base)

            locale_code = locale_obj.code
            print(f"\n{'='*60}")
            print(f"Processing locale: {locale_code}")
            print(f"{'='*60}")

            # Check if translation exists
            existing_trans = (
                db.query(Translation)
                .filter(
                    Translation.content_entry_id == entry.id, Translation.locale_id == locale_obj.id
                )
                .first()
            )

            if existing_trans:
                print("Translation exists, updating...")
                trans_data = (
                    json.loads(existing_trans.translated_data)
                    if isinstance(existing_trans.translated_data, str)
                    else existing_trans.translated_data or {}
                )
            else:
                print("No translation found, creating new one...")
                trans_data = {}
                existing_trans = Translation(
                    content_entry_id=entry.id, locale_id=locale_obj.id, translated_data={}
                )
                db.add(existing_trans)

            # Translate common_labels
            print("\nTranslating common_labels...")
            if "common_labels" not in trans_data:
                trans_data["common_labels"] = {}

            trans_data["common_labels"] = deep_translate(
                common_labels, translation_service, locale_code
            )

            # Translate payment_methods array (names and descriptions)
            payment_methods = base_data.get("payment_methods", [])
            if payment_methods:
                print("\nTranslating payment_methods...")
                trans_data["payment_methods"] = []
                for i, pm in enumerate(payment_methods):
                    if isinstance(pm, dict):
                        print(f"  payment_methods[{i}] ({pm.get('id', 'unknown')}):")
                        trans_data["payment_methods"].append(
                            deep_translate(pm, translation_service, locale_code, depth=2)
                        )
                    else:
                        trans_data["payment_methods"].append(pm)

            # Also translate some other key fields
            for field in ["tagline", "maintenance_message"]:
                if field in base_data and base_data[field]:
                    try:
                        result = translation_service.translate_text(
                            text=base_data[field], target_lang=locale_code, source_lang="en"
                        )
                        trans_data[field] = result.get("translated_text", base_data[field])
                        print(f"Translated {field}: {trans_data[field][:50]}...")
                    except Exception as e:
                        print(f"Failed to translate {field}: {e}")

            # Save
            existing_trans.translated_data = json.dumps(trans_data, ensure_ascii=False)
            db.commit()
            print(f"✅ Saved {locale_code} translation!")

        print(f"\n{'='*60}")
        print("✅ All translations completed!")
        print(f"{'='*60}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
