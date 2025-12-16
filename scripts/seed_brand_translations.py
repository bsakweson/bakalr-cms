#!/usr/bin/env python3
"""
Directly create translations for brands in the database.
This script bypasses the background task system by directly inserting translations.
"""

import json
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db.session import SessionLocal
from backend.models.content import ContentEntry, ContentType
from backend.models.translation import Locale, Translation

# Brand translations - most brand names stay the same, but descriptions get translated
BRAND_TRANSLATIONS = {
    "Bold Hold": {
        "fr": {
            "name": "Bold Hold",
            "description": "Solutions adhésives professionnelles pour perruques et lace front.",
            "short_description": "Colles et adhésifs professionnels",
        },
        "de": {
            "name": "Bold Hold",
            "description": "Professionelle Klebstofflösungen für Perücken und Lace Fronts.",
            "short_description": "Professionelle Kleber und Klebstoffe",
        },
        "es": {
            "name": "Bold Hold",
            "description": "Soluciones adhesivas profesionales para pelucas y lace fronts.",
            "short_description": "Pegamentos y adhesivos profesionales",
        },
    },
    "Andis": {
        "fr": {
            "name": "Andis",
            "description": "Tondeuses et accessoires de coiffure professionnels depuis 1922.",
            "short_description": "Tondeuses professionnelles",
        },
        "de": {
            "name": "Andis",
            "description": "Professionelle Haarschneidemaschinen und Pflegeaccessoires seit 1922.",
            "short_description": "Professionelle Haarschneidemaschinen",
        },
        "es": {
            "name": "Andis",
            "description": "Cortadoras y accesorios de peluquería profesionales desde 1922.",
            "short_description": "Cortadoras profesionales",
        },
    },
    "Wahl": {
        "fr": {
            "name": "Wahl",
            "description": "Leader mondial des tondeuses et produits de toilettage.",
            "short_description": "Tondeuses et rasoirs",
        },
        "de": {
            "name": "Wahl",
            "description": "Weltmarktführer für Haarschneidemaschinen und Pflegeprodukte.",
            "short_description": "Haarschneidemaschinen und Rasierer",
        },
        "es": {
            "name": "Wahl",
            "description": "Líder mundial en cortadoras y productos de aseo.",
            "short_description": "Cortadoras y afeitadoras",
        },
    },
    "Nadula Hair": {
        "fr": {
            "name": "Nadula Hair",
            "description": "Cheveux humains vierges de haute qualité et perruques.",
            "short_description": "Cheveux vierges premium",
        },
        "de": {
            "name": "Nadula Hair",
            "description": "Hochwertige Echthaarprodukte und Perücken.",
            "short_description": "Premium Echthaar",
        },
        "es": {
            "name": "Nadula Hair",
            "description": "Cabello humano virgen de alta calidad y pelucas.",
            "short_description": "Cabello virgen premium",
        },
    },
    "EBIN New York": {
        "fr": {
            "name": "EBIN New York",
            "description": "Produits de beauté et accessoires perruque innovants.",
            "short_description": "Accessoires perruque innovants",
        },
        "de": {
            "name": "EBIN New York",
            "description": "Innovative Schönheitsprodukte und Perückenzubehör.",
            "short_description": "Innovatives Perückenzubehör",
        },
        "es": {
            "name": "EBIN New York",
            "description": "Productos de belleza y accesorios para pelucas innovadores.",
            "short_description": "Accesorios para pelucas innovadores",
        },
    },
    "Tinashe Hair": {
        "fr": {
            "name": "Tinashe Hair",
            "description": "Extensions et perruques en cheveux humains de luxe.",
            "short_description": "Extensions de luxe",
        },
        "de": {
            "name": "Tinashe Hair",
            "description": "Luxus-Echthaarextensions und Perücken.",
            "short_description": "Luxus-Extensions",
        },
        "es": {
            "name": "Tinashe Hair",
            "description": "Extensiones y pelucas de cabello humano de lujo.",
            "short_description": "Extensiones de lujo",
        },
    },
    "got2b": {
        "fr": {
            "name": "got2b",
            "description": "Produits de coiffage audacieux pour des looks créatifs.",
            "short_description": "Coiffage audacieux",
        },
        "de": {
            "name": "got2b",
            "description": "Mutige Stylingprodukte für kreative Looks.",
            "short_description": "Mutiges Styling",
        },
        "es": {
            "name": "got2b",
            "description": "Productos de peinado atrevidos para looks creativos.",
            "short_description": "Peinado atrevido",
        },
    },
    "X-Pression": {
        "fr": {
            "name": "X-Pression",
            "description": "Cheveux à tresser synthétiques premium pour coiffures protectrices.",
            "short_description": "Cheveux à tresser premium",
        },
        "de": {
            "name": "X-Pression",
            "description": "Premium synthetisches Flechthaar für Schutzfrisuren.",
            "short_description": "Premium Flechthaar",
        },
        "es": {
            "name": "X-Pression",
            "description": "Cabello sintético premium para trenzas y peinados protectores.",
            "short_description": "Cabello para trenzas premium",
        },
    },
    "FreeTress": {
        "fr": {
            "name": "FreeTress",
            "description": "Cheveux synthétiques et crochet tresses de qualité.",
            "short_description": "Tresses crochet qualité",
        },
        "de": {
            "name": "FreeTress",
            "description": "Hochwertige synthetische Haare und Häkelzöpfe.",
            "short_description": "Hochwertige Häkelzöpfe",
        },
        "es": {
            "name": "FreeTress",
            "description": "Cabello sintético y trenzas de ganchillo de calidad.",
            "short_description": "Trenzas de ganchillo de calidad",
        },
    },
    "Outre": {
        "fr": {
            "name": "Outre",
            "description": "Perruques et extensions tendance à des prix abordables.",
            "short_description": "Perruques tendance",
        },
        "de": {
            "name": "Outre",
            "description": "Trendige Perücken und Extensions zu erschwinglichen Preisen.",
            "short_description": "Trendige Perücken",
        },
        "es": {
            "name": "Outre",
            "description": "Pelucas y extensiones de moda a precios accesibles.",
            "short_description": "Pelucas de moda",
        },
    },
    "UNice Hair": {
        "fr": {
            "name": "UNice Hair",
            "description": "Cheveux humains vierges de qualité supérieure.",
            "short_description": "Cheveux vierges supérieurs",
        },
        "de": {
            "name": "UNice Hair",
            "description": "Hochwertiges unbehandeltes Echthaar.",
            "short_description": "Hochwertiges Echthaar",
        },
        "es": {
            "name": "UNice Hair",
            "description": "Cabello humano virgen de calidad superior.",
            "short_description": "Cabello virgen superior",
        },
    },
    "Beauty Forever": {
        "fr": {
            "name": "Beauty Forever",
            "description": "Extensions et perruques abordables et de qualité.",
            "short_description": "Extensions abordables",
        },
        "de": {
            "name": "Beauty Forever",
            "description": "Erschwingliche und hochwertige Extensions und Perücken.",
            "short_description": "Erschwingliche Extensions",
        },
        "es": {
            "name": "Beauty Forever",
            "description": "Extensiones y pelucas asequibles y de calidad.",
            "short_description": "Extensiones asequibles",
        },
    },
    "Sensationnel": {
        "fr": {
            "name": "Sensationnel",
            "description": "Leader des cheveux synthétiques et naturels innovants.",
            "short_description": "Cheveux innovants",
        },
        "de": {
            "name": "Sensationnel",
            "description": "Marktführer für innovative synthetische und natürliche Haare.",
            "short_description": "Innovative Haare",
        },
        "es": {
            "name": "Sensationnel",
            "description": "Líder en cabello sintético y natural innovador.",
            "short_description": "Cabello innovador",
        },
    },
    "Cantu": {
        "fr": {
            "name": "Cantu",
            "description": "Soins capillaires naturels au beurre de karité.",
            "short_description": "Soins au karité",
        },
        "de": {
            "name": "Cantu",
            "description": "Natürliche Haarpflege mit Sheabutter.",
            "short_description": "Sheabutter-Pflege",
        },
        "es": {
            "name": "Cantu",
            "description": "Cuidado capilar natural con manteca de karité.",
            "short_description": "Cuidado con karité",
        },
    },
    "Mielle Organics": {
        "fr": {
            "name": "Mielle Organics",
            "description": "Soins capillaires biologiques et naturels.",
            "short_description": "Soins bio",
        },
        "de": {
            "name": "Mielle Organics",
            "description": "Bio und natürliche Haarpflege.",
            "short_description": "Bio-Pflege",
        },
        "es": {
            "name": "Mielle Organics",
            "description": "Cuidado capilar orgánico y natural.",
            "short_description": "Cuidado orgánico",
        },
    },
    "Bakalr Hair": {
        "fr": {
            "name": "Bakalr Hair",
            "description": "Notre marque maison de cheveux premium et accessoires.",
            "short_description": "Marque maison premium",
        },
        "de": {
            "name": "Bakalr Hair",
            "description": "Unsere Hausmarke für Premium-Haare und Zubehör.",
            "short_description": "Premium-Hausmarke",
        },
        "es": {
            "name": "Bakalr Hair",
            "description": "Nuestra marca propia de cabello premium y accesorios.",
            "short_description": "Marca propia premium",
        },
    },
    "SheaMoisture": {
        "fr": {
            "name": "SheaMoisture",
            "description": "Produits de beauté naturels au commerce équitable.",
            "short_description": "Beauté équitable",
        },
        "de": {
            "name": "SheaMoisture",
            "description": "Natürliche Fair-Trade-Schönheitsprodukte.",
            "short_description": "Fair-Trade-Schönheit",
        },
        "es": {
            "name": "SheaMoisture",
            "description": "Productos de belleza naturales de comercio justo.",
            "short_description": "Belleza de comercio justo",
        },
    },
    "ISEE Hair": {
        "fr": {
            "name": "ISEE Hair",
            "description": "Cheveux humains brésiliens de haute qualité.",
            "short_description": "Cheveux brésiliens",
        },
        "de": {
            "name": "ISEE Hair",
            "description": "Hochwertiges brasilianisches Echthaar.",
            "short_description": "Brasilianisches Haar",
        },
        "es": {
            "name": "ISEE Hair",
            "description": "Cabello humano brasileño de alta calidad.",
            "short_description": "Cabello brasileño",
        },
    },
    "Ardell": {
        "fr": {
            "name": "Ardell",
            "description": "Leader mondial des faux cils et accessoires.",
            "short_description": "Faux cils",
        },
        "de": {
            "name": "Ardell",
            "description": "Weltmarktführer für künstliche Wimpern und Zubehör.",
            "short_description": "Künstliche Wimpern",
        },
        "es": {
            "name": "Ardell",
            "description": "Líder mundial en pestañas postizas y accesorios.",
            "short_description": "Pestañas postizas",
        },
    },
    "BaBylissPRO": {
        "fr": {
            "name": "BaBylissPRO",
            "description": "Outils de coiffure professionnels de haute performance.",
            "short_description": "Outils professionnels",
        },
        "de": {
            "name": "BaBylissPRO",
            "description": "Professionelle Hochleistungs-Styling-Werkzeuge.",
            "short_description": "Professionelle Werkzeuge",
        },
        "es": {
            "name": "BaBylissPRO",
            "description": "Herramientas de peinado profesionales de alto rendimiento.",
            "short_description": "Herramientas profesionales",
        },
    },
}


def main():
    print("=" * 60)
    print("Direct Brand Translation Seeder")
    print("=" * 60)

    db = SessionLocal()

    try:
        # Get all locales
        locales = db.query(Locale).filter(Locale.is_enabled == True).all()
        locale_map = {loc.code: loc for loc in locales}
        print(f"\nFound locales: {list(locale_map.keys())}")

        # Get content type for brand
        brand_type = db.query(ContentType).filter(ContentType.api_id == "brand").first()
        if not brand_type:
            print("ERROR: Brand content type not found!")
            return

        # Get all brands
        brands = db.query(ContentEntry).filter(ContentEntry.content_type_id == brand_type.id).all()
        print(f"Found {len(brands)} brands")

        created_count = 0
        skipped_count = 0

        for brand in brands:
            # Parse brand data
            try:
                data = json.loads(brand.data) if isinstance(brand.data, str) else brand.data
            except (json.JSONDecodeError, TypeError):
                data = {}

            brand_name = data.get("name", "Unknown")
            print(f"\nProcessing: {brand_name}")

            # Check if we have translations for this brand
            translations = BRAND_TRANSLATIONS.get(brand_name, None)

            for locale_code in ["fr", "de", "es"]:
                if locale_code not in locale_map:
                    continue

                locale = locale_map[locale_code]

                # Check if translation already exists
                existing = (
                    db.query(Translation)
                    .filter(
                        Translation.content_entry_id == brand.id, Translation.locale_id == locale.id
                    )
                    .first()
                )

                if existing:
                    print(f"  ✓ {locale_code}: Already exists")
                    skipped_count += 1
                    continue

                # Get translation data
                if translations and locale_code in translations:
                    translated_data = translations[locale_code]
                else:
                    print(f"  ⚠ {locale_code}: No translation mapping, skipping")
                    continue

                # Create translation
                translation = Translation(
                    content_entry_id=brand.id,
                    locale_id=locale.id,
                    translated_data=json.dumps(translated_data),
                    status="completed",
                    translation_service="manual",
                    quality_score=1.0,
                )
                db.add(translation)
                print(f"  ✓ {locale_code}: Created - {translated_data['name']}")
                created_count += 1

        db.commit()

        print("\n" + "=" * 60)
        print("Translation seeding complete!")
        print(f"  Created: {created_count}")
        print(f"  Skipped: {skipped_count}")
        print("=" * 60)

    except Exception as e:
        print(f"ERROR: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
