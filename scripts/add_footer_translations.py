#!/usr/bin/env python3
"""
Add footer translations (we_accept) using the CMS auto-translation service.
Run inside Docker: cat scripts/add_footer_translations.py | docker exec -i bakalr-backend python3 -
"""

from backend.core.translation_service import TranslationService
from backend.db.session import SessionLocal
from backend.models.content import ContentEntry
from backend.models.translation import Locale, Translation

# English source text - the translation service will auto-translate
ENGLISH_FOOTER = {"we_accept": "We accept:"}

SITE_SETTINGS_ID = "34850f0b-d781-4adf-94be-453461f5227e"


def translate_footer():
    db = SessionLocal()
    translation_service = TranslationService()

    try:
        # Get site settings entry
        entry = db.query(ContentEntry).filter(ContentEntry.id == SITE_SETTINGS_ID).first()

        if not entry:
            print(f"❌ Site settings entry not found: {SITE_SETTINGS_ID}")
            return

        print(f"Found entry: {entry.slug}")

        # Get all enabled locales
        locales = db.query(Locale).filter(Locale.is_enabled == True).all()
        print(f"Found {len(locales)} enabled locales: {[l.code for l in locales]}")

        # Get all translations for this entry
        translations = db.query(Translation).filter(Translation.content_entry_id == entry.id).all()

        print(f"\nUpdating {len(translations)} translations...")

        updated_count = 0
        for trans in translations:
            # Get locale
            locale_obj = db.query(Locale).filter(Locale.id == trans.locale_id).first()
            if not locale_obj:
                continue
            locale_code = locale_obj.code

            # Skip English - it's the source
            if locale_code == "en":
                continue

            # Parse existing data
            import json

            if isinstance(trans.translated_data, str):
                data = json.loads(trans.translated_data)
            else:
                data = trans.translated_data or {}

            # Ensure structure exists
            if "common_labels" not in data:
                data["common_labels"] = {}
            if "footer" not in data["common_labels"]:
                data["common_labels"]["footer"] = {}

            # Auto-translate the footer text
            try:
                # TranslationService.translate_text(text, target_lang, source_lang=None)
                # Returns dict with "translated_text" key
                result = translation_service.translate_text(
                    text=ENGLISH_FOOTER["we_accept"], target_lang=locale_code, source_lang="en"
                )
                translated_text = result.get("translated_text", ENGLISH_FOOTER["we_accept"])
                data["common_labels"]["footer"]["we_accept"] = translated_text
                trans.translated_data = json.dumps(data)
                print(f"  ✅ {locale_code}: {translated_text}")
                updated_count += 1
            except Exception as e:
                print(f"  ❌ {locale_code}: Translation failed - {e}")

        db.commit()
        print(f"\n✅ Auto-translated footer to {updated_count} locales!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


def main():
    translate_footer()


if __name__ == "__main__":
    main()
