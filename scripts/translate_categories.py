#!/usr/bin/env python3
"""
Batch translate all categories to French, German, and Spanish.
This script creates translations for all category entries in the CMS.
"""

import time

import requests

# Configuration
CMS_URL = "http://localhost:8000"
API_KEY = "bk_p4mPH5PGxFb9yk3jd9O12ChtBcCt8fGfDlagg70tobI"

HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# Translation mappings for common category terms
TRANSLATIONS = {
    "fr": {
        "Hair Styling": "Coiffure",
        "Style your hair with confidence using our professional-grade gels, sprays, and styling products.": "Coiffez vos cheveux en toute confiance grâce à nos gels, sprays et produits coiffants de qualité professionnelle.",
        "Beard Care": "Soins de la Barbe",
        "Premium beard oils, balms, and grooming tools for the modern gentleman.": "Huiles à barbe, baumes et outils de toilettage haut de gamme pour l'homme moderne.",
        "Shaving": "Rasage",
        "Classic and modern shaving essentials for a smooth, comfortable shave.": "Essentiels de rasage classiques et modernes pour un rasage doux et confortable.",
        "Skincare": "Soins de la Peau",
        "Men's skincare products to cleanse, moisturize, and protect your skin.": "Produits de soins pour hommes pour nettoyer, hydrater et protéger votre peau.",
        "Fragrances": "Parfums",
        "Distinctive colognes and fragrances for every occasion.": "Eaux de Cologne et parfums distinctifs pour chaque occasion.",
        "Body Care": "Soins Corporels",
        "Body washes, lotions, and grooming essentials for head-to-toe care.": "Gels douche, lotions et essentiels de toilettage pour un soin de la tête aux pieds.",
        "Hair Care": "Soins Capillaires",
        "Shampoos, conditioners, and treatments for healthy, great-looking hair.": "Shampoings, après-shampoings et traitements pour des cheveux sains et beaux.",
        "Accessories": "Accessoires",
        "Grooming tools, bags, and accessories to complete your routine.": "Outils de toilettage, sacs et accessoires pour compléter votre routine.",
        "Gift Sets": "Coffrets Cadeaux",
        "Curated gift sets perfect for any occasion.": "Coffrets cadeaux sélectionnés parfaits pour toute occasion.",
        "New Arrivals": "Nouveautés",
        "The latest additions to our collection.": "Les dernières nouveautés de notre collection.",
    },
    "de": {
        "Hair Styling": "Haarstyling",
        "Style your hair with confidence using our professional-grade gels, sprays, and styling products.": "Stylen Sie Ihr Haar selbstbewusst mit unseren professionellen Gels, Sprays und Stylingprodukten.",
        "Beard Care": "Bartpflege",
        "Premium beard oils, balms, and grooming tools for the modern gentleman.": "Premium-Bartöle, Balsame und Pflegewerkzeuge für den modernen Gentleman.",
        "Shaving": "Rasur",
        "Classic and modern shaving essentials for a smooth, comfortable shave.": "Klassische und moderne Rasur-Essentials für eine glatte, angenehme Rasur.",
        "Skincare": "Hautpflege",
        "Men's skincare products to cleanse, moisturize, and protect your skin.": "Herrenpflegeprodukte zum Reinigen, Befeuchten und Schützen Ihrer Haut.",
        "Fragrances": "Düfte",
        "Distinctive colognes and fragrances for every occasion.": "Unverwechselbare Kölnisch Wasser und Düfte für jeden Anlass.",
        "Body Care": "Körperpflege",
        "Body washes, lotions, and grooming essentials for head-to-toe care.": "Duschgels, Lotionen und Pflege-Essentials für die Pflege von Kopf bis Fuß.",
        "Hair Care": "Haarpflege",
        "Shampoos, conditioners, and treatments for healthy, great-looking hair.": "Shampoos, Conditioner und Behandlungen für gesundes, toll aussehendes Haar.",
        "Accessories": "Zubehör",
        "Grooming tools, bags, and accessories to complete your routine.": "Pflegewerkzeuge, Taschen und Zubehör zur Vervollständigung Ihrer Routine.",
        "Gift Sets": "Geschenksets",
        "Curated gift sets perfect for any occasion.": "Kuratierte Geschenksets, perfekt für jeden Anlass.",
        "New Arrivals": "Neuheiten",
        "The latest additions to our collection.": "Die neuesten Ergänzungen unserer Kollektion.",
    },
    "es": {
        "Hair Styling": "Estilizado del Cabello",
        "Style your hair with confidence using our professional-grade gels, sprays, and styling products.": "Peina tu cabello con confianza usando nuestros geles, sprays y productos de estilizado de grado profesional.",
        "Beard Care": "Cuidado de la Barba",
        "Premium beard oils, balms, and grooming tools for the modern gentleman.": "Aceites para barba premium, bálsamos y herramientas de aseo para el caballero moderno.",
        "Shaving": "Afeitado",
        "Classic and modern shaving essentials for a smooth, comfortable shave.": "Esenciales de afeitado clásicos y modernos para un afeitado suave y cómodo.",
        "Skincare": "Cuidado de la Piel",
        "Men's skincare products to cleanse, moisturize, and protect your skin.": "Productos de cuidado de la piel para hombres para limpiar, hidratar y proteger tu piel.",
        "Fragrances": "Fragancias",
        "Distinctive colognes and fragrances for every occasion.": "Colonias y fragancias distintivas para cada ocasión.",
        "Body Care": "Cuidado Corporal",
        "Body washes, lotions, and grooming essentials for head-to-toe care.": "Geles de baño, lociones y esenciales de aseo para el cuidado de pies a cabeza.",
        "Hair Care": "Cuidado del Cabello",
        "Shampoos, conditioners, and treatments for healthy, great-looking hair.": "Champús, acondicionadores y tratamientos para un cabello sano y hermoso.",
        "Accessories": "Accesorios",
        "Grooming tools, bags, and accessories to complete your routine.": "Herramientas de aseo, bolsas y accesorios para completar tu rutina.",
        "Gift Sets": "Sets de Regalo",
        "Curated gift sets perfect for any occasion.": "Sets de regalo seleccionados perfectos para cualquier ocasión.",
        "New Arrivals": "Novedades",
        "The latest additions to our collection.": "Las últimas incorporaciones a nuestra colección.",
    },
}


def get_all_categories():
    """Fetch all categories from CMS."""
    response = requests.get(
        f"{CMS_URL}/api/v1/content/entries",
        headers=HEADERS,
        params={"content_type_slug": "category", "page_size": 100},
    )
    response.raise_for_status()
    data = response.json()
    return data.get("items", [])


def get_locales():
    """Fetch all available locales."""
    response = requests.get(f"{CMS_URL}/api/v1/translation/locales", headers=HEADERS)
    response.raise_for_status()
    return response.json()


def translate_text(text, locale_code):
    """Get translation for text, using mapping or returning original."""
    if locale_code in TRANSLATIONS:
        return TRANSLATIONS[locale_code].get(text, text)
    return text


def create_translation(entry_id, locale_code, translated_data):
    """Create a translation for a content entry."""
    # First check if translation exists
    check_response = requests.get(
        f"{CMS_URL}/api/v1/translation/entries/{entry_id}/translations/{locale_code}",
        headers=HEADERS,
    )

    if check_response.status_code == 200:
        print(f"  Translation for {locale_code} already exists, skipping...")
        return True

    # Use the translate endpoint
    response = requests.post(
        f"{CMS_URL}/api/v1/translation/translate",
        headers=HEADERS,
        json={
            "content_entry_id": entry_id,
            "target_locale_ids": [],  # Empty means all enabled locales
            "force_retranslate": False,
        },
    )

    if response.status_code == 200:
        print(f"  Queued translation for {locale_code}")
        return True
    else:
        print(f"  Failed to create translation: {response.status_code} - {response.text}")
        return False


def main():
    print("=" * 60)
    print("Category Translation Script")
    print("=" * 60)

    # Get locales
    print("\nFetching locales...")
    locales = get_locales()
    locale_map = {loc["code"]: loc["id"] for loc in locales}
    print(f"Found locales: {list(locale_map.keys())}")

    # Get categories
    print("\nFetching categories...")
    categories = get_all_categories()
    print(f"Found {len(categories)} categories")

    # Target locales (exclude English which is the default)
    target_locales = ["fr", "de", "es"]

    # Process each category
    for category in categories:
        entry_id = category["id"]
        name = category.get("data", {}).get("name", "Unknown")
        print(f"\nProcessing: {name} ({entry_id})")

        for locale_code in target_locales:
            if locale_code not in locale_map:
                print(f"  Locale {locale_code} not available, skipping...")
                continue

            locale_id = locale_map[locale_code]

            # Check if translation exists
            check_response = requests.get(
                f"{CMS_URL}/api/v1/translation/entries/{entry_id}/translations/{locale_code}",
                headers=HEADERS,
            )

            if check_response.status_code == 200:
                print(f"  ✓ {locale_code}: Already translated")
                continue

            # Create translation using our mapping
            original_name = category.get("data", {}).get("name", "")
            original_desc = category.get("data", {}).get("description", "")

            translated_name = translate_text(original_name, locale_code)
            translated_desc = translate_text(original_desc, locale_code)

            # If we have a translation in our mapping, create it directly
            if translated_name != original_name or translated_desc != original_desc:
                # Try to create translation via the entries endpoint
                create_response = requests.post(
                    f"{CMS_URL}/api/v1/translation/entries/{entry_id}/translations",
                    headers=HEADERS,
                    json={
                        "locale_code": locale_code,
                        "translated_data": {
                            "name": translated_name,
                            "description": translated_desc,
                        },
                    },
                )

                if create_response.status_code in [200, 201]:
                    print(f"  ✓ {locale_code}: Created - {translated_name}")
                else:
                    # Try using the bulk translate endpoint instead
                    translate_response = requests.post(
                        f"{CMS_URL}/api/v1/translation/translate",
                        headers=HEADERS,
                        json={"content_entry_id": entry_id, "target_locale_ids": [locale_id]},
                    )
                    if translate_response.status_code == 200:
                        print(f"  ⏳ {locale_code}: Queued for auto-translation")
                    else:
                        print(f"  ✗ {locale_code}: Failed - {create_response.status_code}")
            else:
                # No mapping available, use auto-translate
                translate_response = requests.post(
                    f"{CMS_URL}/api/v1/translation/translate",
                    headers=HEADERS,
                    json={"content_entry_id": entry_id, "target_locale_ids": [locale_id]},
                )
                if translate_response.status_code == 200:
                    print(f"  ⏳ {locale_code}: Queued for auto-translation")
                else:
                    print(f"  ✗ {locale_code}: Failed to queue")

        # Small delay to avoid overwhelming the API
        time.sleep(0.1)

    print("\n" + "=" * 60)
    print("Translation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
