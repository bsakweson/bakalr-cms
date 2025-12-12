#!/usr/bin/env python3
"""
Add missing product detail page labels to CMS and auto-translate them.
Run inside Docker: cat scripts/add_product_detail_labels.py | docker exec -i bakalr-backend python3 -
"""

import json

from backend.core.translation_service import TranslationService
from backend.db.session import SessionLocal
from backend.models.content import ContentEntry
from backend.models.translation import Locale, Translation

SITE_SETTINGS_ID = "34850f0b-d781-4adf-94be-453461f5227e"

# New labels to add to the English base content
NEW_LABELS = {
    "cart": {"add_to_cart": "Add to Cart", "add_more": "Add More"},
    "product_detail": {
        "specifications": "Specifications",
        "selected": "Selected:",
        "length": "Length:",
        "no_image": "No Image Available",
        "sku": "SKU:",
        "related_products": "Related Products",
        "view_product": "View Product",
        "inches": "inches",
    },
}


def add_labels():
    db = SessionLocal()
    translation_service = TranslationService()

    try:
        # 1. Update English base content
        entry = db.query(ContentEntry).filter(ContentEntry.id == SITE_SETTINGS_ID).first()

        if not entry:
            print(f"❌ Site settings entry not found: {SITE_SETTINGS_ID}")
            return

        print(f"Found entry: {entry.slug}")

        # Parse existing data
        data = json.loads(entry.data) if isinstance(entry.data, str) else entry.data

        if "common_labels" not in data:
            data["common_labels"] = {}

        # Add new labels to English base
        labels_added = []
        for group, labels in NEW_LABELS.items():
            if group not in data["common_labels"]:
                data["common_labels"][group] = {}
            for key, value in labels.items():
                if key not in data["common_labels"][group]:
                    data["common_labels"][group][key] = value
                    labels_added.append(f"{group}.{key}")

        # Save English base
        entry.data = json.dumps(data)
        db.commit()
        print(f"✅ Added {len(labels_added)} new labels to English base:")
        for label in labels_added:
            print(f"   - {label}")

        # 2. Auto-translate to all locales
        locales = db.query(Locale).filter(Locale.is_enabled == True).all()
        locale_codes = [l.code for l in locales if l.code != "en"]
        print(f"\nTranslating to {len(locale_codes)} locales: {locale_codes}")

        translations = db.query(Translation).filter(Translation.content_entry_id == entry.id).all()

        for trans in translations:
            locale_obj = db.query(Locale).filter(Locale.id == trans.locale_id).first()
            if not locale_obj or locale_obj.code == "en":
                continue

            locale_code = locale_obj.code
            print(f"\n  Translating to {locale_code}...")

            # Parse translated data
            trans_data = (
                json.loads(trans.translated_data)
                if isinstance(trans.translated_data, str)
                else trans.translated_data or {}
            )

            if "common_labels" not in trans_data:
                trans_data["common_labels"] = {}

            # Translate each new label group
            for group, labels in NEW_LABELS.items():
                if group not in trans_data["common_labels"]:
                    trans_data["common_labels"][group] = {}

                for key, english_text in labels.items():
                    if key not in trans_data["common_labels"][group]:
                        try:
                            result = translation_service.translate_text(
                                text=english_text, target_lang=locale_code, source_lang="en"
                            )
                            translated = result.get("translated_text", english_text)
                            trans_data["common_labels"][group][key] = translated
                            print(f"    ✅ {group}.{key}: {translated}")
                        except Exception as e:
                            print(f"    ❌ {group}.{key}: {e}")
                            trans_data["common_labels"][group][key] = english_text

            trans.translated_data = json.dumps(trans_data)

        db.commit()
        print("\n✅ Completed! All labels added and translated.")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    add_labels()
