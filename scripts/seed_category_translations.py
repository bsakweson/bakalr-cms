#!/usr/bin/env python3
"""
Directly create translations for categories in the database.
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

# Translation mappings for categories
CATEGORY_TRANSLATIONS = {
    "Hair Styling": {
        "fr": {
            "name": "Coiffure",
            "description": "Coiffez vos cheveux avec confiance grâce à nos gels, sprays et produits coiffants de qualité professionnelle.",
        },
        "de": {
            "name": "Haarstyling",
            "description": "Stylen Sie Ihr Haar selbstbewusst mit unseren professionellen Gels, Sprays und Stylingprodukten.",
        },
        "es": {
            "name": "Estilizado del Cabello",
            "description": "Peina tu cabello con confianza usando nuestros geles, sprays y productos de estilizado de grado profesional.",
        },
    },
    "Hair Care": {
        "fr": {
            "name": "Soins Capillaires",
            "description": "Produits essentiels pour des cheveux sains et magnifiques.",
        },
        "de": {
            "name": "Haarpflege",
            "description": "Wesentliche Produkte für gesundes und schönes Haar.",
        },
        "es": {
            "name": "Cuidado del Cabello",
            "description": "Productos esenciales para un cabello sano y hermoso.",
        },
    },
    "Wigs": {
        "fr": {
            "name": "Perruques",
            "description": "Perruques de haute qualité pour tous les styles.",
        },
        "de": {"name": "Perücken", "description": "Hochwertige Perücken für jeden Stil."},
        "es": {"name": "Pelucas", "description": "Pelucas de alta calidad para todos los estilos."},
    },
    "Wigs & Extensions": {
        "fr": {
            "name": "Perruques & Extensions",
            "description": "Collection complète de perruques et extensions de cheveux.",
        },
        "de": {
            "name": "Perücken & Extensions",
            "description": "Komplette Kollektion von Perücken und Haarverlängerungen.",
        },
        "es": {
            "name": "Pelucas y Extensiones",
            "description": "Colección completa de pelucas y extensiones de cabello.",
        },
    },
    "Hair Extensions": {
        "fr": {
            "name": "Extensions de Cheveux",
            "description": "Extensions de cheveux naturels de première qualité.",
        },
        "de": {
            "name": "Haarverlängerungen",
            "description": "Erstklassige natürliche Haarverlängerungen.",
        },
        "es": {
            "name": "Extensiones de Cabello",
            "description": "Extensiones de cabello natural de primera calidad.",
        },
    },
    "Hair Tools": {
        "fr": {
            "name": "Outils Capillaires",
            "description": "Outils professionnels pour coiffer vos cheveux.",
        },
        "de": {
            "name": "Haarwerkzeuge",
            "description": "Professionelle Werkzeuge zum Stylen Ihrer Haare.",
        },
        "es": {
            "name": "Herramientas para el Cabello",
            "description": "Herramientas profesionales para peinar tu cabello.",
        },
    },
    "Skincare": {
        "fr": {
            "name": "Soins de la Peau",
            "description": "Produits de soins pour une peau saine et éclatante.",
        },
        "de": {
            "name": "Hautpflege",
            "description": "Pflegeprodukte für gesunde und strahlende Haut.",
        },
        "es": {
            "name": "Cuidado de la Piel",
            "description": "Productos de cuidado para una piel sana y radiante.",
        },
    },
    "Cosmetics": {
        "fr": {"name": "Cosmétiques", "description": "Produits cosmétiques de haute qualité."},
        "de": {"name": "Kosmetik", "description": "Hochwertige Kosmetikprodukte."},
        "es": {"name": "Cosméticos", "description": "Productos cosméticos de alta calidad."},
    },
    "Nails": {
        "fr": {"name": "Ongles", "description": "Tout pour des ongles parfaits."},
        "de": {"name": "Nägel", "description": "Alles für perfekte Nägel."},
        "es": {"name": "Uñas", "description": "Todo para uñas perfectas."},
    },
    "Lace Front Wigs": {
        "fr": {
            "name": "Perruques Lace Front",
            "description": "Perruques lace front pour un look naturel.",
        },
        "de": {
            "name": "Lace Front Perücken",
            "description": "Lace Front Perücken für einen natürlichen Look.",
        },
        "es": {
            "name": "Pelucas Lace Front",
            "description": "Pelucas lace front para un look natural.",
        },
    },
    "Full Lace Wigs": {
        "fr": {
            "name": "Perruques Full Lace",
            "description": "Perruques full lace pour une polyvalence maximale.",
        },
        "de": {
            "name": "Full Lace Perücken",
            "description": "Full Lace Perücken für maximale Vielseitigkeit.",
        },
        "es": {
            "name": "Pelucas Full Lace",
            "description": "Pelucas full lace para máxima versatilidad.",
        },
    },
    "Glueless Wigs": {
        "fr": {
            "name": "Perruques Sans Colle",
            "description": "Perruques sans colle faciles à porter.",
        },
        "de": {
            "name": "Klebefreie Perücken",
            "description": "Klebefreie Perücken, einfach zu tragen.",
        },
        "es": {
            "name": "Pelucas Sin Pegamento",
            "description": "Pelucas sin pegamento fáciles de usar.",
        },
    },
    "Colored Wigs": {
        "fr": {
            "name": "Perruques Colorées",
            "description": "Perruques colorées pour un style audacieux.",
        },
        "de": {
            "name": "Farbige Perücken",
            "description": "Farbige Perücken für einen mutigen Stil.",
        },
        "es": {
            "name": "Pelucas de Colores",
            "description": "Pelucas de colores para un estilo atrevido.",
        },
    },
    "Closures": {
        "fr": {"name": "Closures", "description": "Closures de haute qualité pour vos perruques."},
        "de": {"name": "Closures", "description": "Hochwertige Closures für Ihre Perücken."},
        "es": {"name": "Closures", "description": "Closures de alta calidad para tus pelucas."},
    },
    "Frontals": {
        "fr": {
            "name": "Frontales",
            "description": "Frontales pour un look naturel et sans couture.",
        },
        "de": {
            "name": "Frontals",
            "description": "Frontals für einen natürlichen und nahtlosen Look.",
        },
        "es": {
            "name": "Frontales",
            "description": "Frontales para un look natural y sin costuras.",
        },
    },
    "Braiding Hair": {
        "fr": {
            "name": "Cheveux à Tresser",
            "description": "Cheveux synthétiques pour tresses et coiffures protectrices.",
        },
        "de": {
            "name": "Flechthaar",
            "description": "Synthetisches Haar für Zöpfe und Schutzfrisuren.",
        },
        "es": {
            "name": "Cabello para Trenzas",
            "description": "Cabello sintético para trenzas y peinados protectores.",
        },
    },
    "Shop by Texture": {
        "fr": {
            "name": "Acheter par Texture",
            "description": "Trouvez le produit parfait selon votre texture de cheveux.",
        },
        "de": {
            "name": "Nach Textur einkaufen",
            "description": "Finden Sie das perfekte Produkt für Ihre Haartextur.",
        },
        "es": {
            "name": "Comprar por Textura",
            "description": "Encuentra el producto perfecto según tu textura de cabello.",
        },
    },
    "Straight": {
        "fr": {"name": "Lisse", "description": "Cheveux lisses et soyeux."},
        "de": {"name": "Glatt", "description": "Glattes und seidiges Haar."},
        "es": {"name": "Liso", "description": "Cabello liso y sedoso."},
    },
    "Body Wave": {
        "fr": {"name": "Ondulé", "description": "Ondulations naturelles et élégantes."},
        "de": {"name": "Körperwelle", "description": "Natürliche und elegante Wellen."},
        "es": {"name": "Ondulado", "description": "Ondas naturales y elegantes."},
    },
    "Curly": {
        "fr": {"name": "Bouclé", "description": "Boucles définies et rebondissantes."},
        "de": {"name": "Lockig", "description": "Definierte und federnde Locken."},
        "es": {"name": "Rizado", "description": "Rizos definidos y con rebote."},
    },
    "Deep Wave": {
        "fr": {"name": "Vague Profonde", "description": "Vagues profondes et volumineuses."},
        "de": {"name": "Tiefe Welle", "description": "Tiefe und voluminöse Wellen."},
        "es": {"name": "Onda Profunda", "description": "Ondas profundas y voluminosas."},
    },
    "Water Wave": {
        "fr": {"name": "Vague d'Eau", "description": "Texture vague d'eau naturelle."},
        "de": {"name": "Wasserwelle", "description": "Natürliche Wasserwellentextur."},
        "es": {"name": "Onda de Agua", "description": "Textura de onda de agua natural."},
    },
    "Loose Wave": {
        "fr": {"name": "Vague Lâche", "description": "Ondulations légères et naturelles."},
        "de": {"name": "Lockere Welle", "description": "Leichte und natürliche Wellen."},
        "es": {"name": "Onda Suelta", "description": "Ondas ligeras y naturales."},
    },
    "Kinky Curly": {
        "fr": {"name": "Crépu Bouclé", "description": "Texture crépue et bouclée authentique."},
        "de": {"name": "Kinky Lockig", "description": "Authentische kinky lockige Textur."},
        "es": {"name": "Rizado Afro", "description": "Textura rizada afro auténtica."},
    },
    "Kinky Straight": {
        "fr": {"name": "Crépu Lisse", "description": "Texture crépue lissée naturelle."},
        "de": {"name": "Kinky Glatt", "description": "Natürliche kinky glatte Textur."},
        "es": {"name": "Liso Afro", "description": "Textura afro alisada natural."},
    },
    "Brazilian Hair": {
        "fr": {
            "name": "Cheveux Brésiliens",
            "description": "Cheveux vierges brésiliens de première qualité.",
        },
        "de": {
            "name": "Brasilianisches Haar",
            "description": "Erstklassiges brasilianisches Echthaar.",
        },
        "es": {
            "name": "Cabello Brasileño",
            "description": "Cabello virgen brasileño de primera calidad.",
        },
    },
    "Peruvian Hair": {
        "fr": {"name": "Cheveux Péruviens", "description": "Cheveux vierges péruviens luxueux."},
        "de": {"name": "Peruanisches Haar", "description": "Luxuriöses peruanisches Echthaar."},
        "es": {"name": "Cabello Peruano", "description": "Cabello virgen peruano de lujo."},
    },
    "Malaysian Hair": {
        "fr": {"name": "Cheveux Malaisiens", "description": "Cheveux vierges malaisiens soyeux."},
        "de": {"name": "Malaysisches Haar", "description": "Seidiges malaysisches Echthaar."},
        "es": {"name": "Cabello Malayo", "description": "Cabello virgen malayo sedoso."},
    },
    "Indian Hair": {
        "fr": {"name": "Cheveux Indiens", "description": "Cheveux vierges indiens naturels."},
        "de": {"name": "Indisches Haar", "description": "Natürliches indisches Echthaar."},
        "es": {"name": "Cabello Indio", "description": "Cabello virgen indio natural."},
    },
    "Cambodian Hair": {
        "fr": {"name": "Cheveux Cambodgiens", "description": "Cheveux vierges cambodgiens épais."},
        "de": {
            "name": "Kambodschanisches Haar",
            "description": "Dickes kambodschanisches Echthaar.",
        },
        "es": {"name": "Cabello Camboyano", "description": "Cabello virgen camboyano grueso."},
    },
    "Vietnamese Hair": {
        "fr": {
            "name": "Cheveux Vietnamiens",
            "description": "Cheveux vierges vietnamiens de qualité.",
        },
        "de": {
            "name": "Vietnamesisches Haar",
            "description": "Hochwertiges vietnamesisches Echthaar.",
        },
        "es": {
            "name": "Cabello Vietnamita",
            "description": "Cabello virgen vietnamita de calidad.",
        },
    },
    "Burmese Hair": {
        "fr": {"name": "Cheveux Birmans", "description": "Cheveux vierges birmans rares."},
        "de": {"name": "Birmanisches Haar", "description": "Seltenes birmanisches Echthaar."},
        "es": {"name": "Cabello Birmano", "description": "Cabello virgen birmano raro."},
    },
    "Wig Accessories": {
        "fr": {
            "name": "Accessoires Perruques",
            "description": "Accessoires essentiels pour perruques.",
        },
        "de": {"name": "Perückenzubehör", "description": "Wesentliches Zubehör für Perücken."},
        "es": {
            "name": "Accesorios para Pelucas",
            "description": "Accesorios esenciales para pelucas.",
        },
    },
    "Wig Caps": {
        "fr": {"name": "Bonnets Perruque", "description": "Bonnets de protection pour perruques."},
        "de": {"name": "Perückenkappen", "description": "Schutzkappen für Perücken."},
        "es": {"name": "Gorros para Pelucas", "description": "Gorros de protección para pelucas."},
    },
    "Wig Glue & Adhesive": {
        "fr": {
            "name": "Colle & Adhésif Perruque",
            "description": "Colles et adhésifs pour perruques.",
        },
        "de": {
            "name": "Perückenkleber & Klebstoff",
            "description": "Kleber und Klebstoffe für Perücken.",
        },
        "es": {
            "name": "Pegamento y Adhesivo para Pelucas",
            "description": "Pegamentos y adhesivos para pelucas.",
        },
    },
    "Lace Melting & Tint": {
        "fr": {
            "name": "Fonte & Teinture Lace",
            "description": "Produits pour fondre et teinter le lace.",
        },
        "de": {
            "name": "Lace Schmelzen & Tönen",
            "description": "Produkte zum Schmelzen und Tönen von Lace.",
        },
        "es": {
            "name": "Fusión y Tinte de Lace",
            "description": "Productos para fundir y teñir el lace.",
        },
    },
    "Shampoo & Conditioner": {
        "fr": {
            "name": "Shampooing & Après-shampooing",
            "description": "Nettoyage et conditionnement des cheveux.",
        },
        "de": {"name": "Shampoo & Conditioner", "description": "Reinigung und Pflege der Haare."},
        "es": {
            "name": "Champú y Acondicionador",
            "description": "Limpieza y acondicionamiento del cabello.",
        },
    },
    "Treatments & Oils": {
        "fr": {
            "name": "Traitements & Huiles",
            "description": "Traitements nourrissants et huiles capillaires.",
        },
        "de": {"name": "Behandlungen & Öle", "description": "Nährende Behandlungen und Haaröle."},
        "es": {
            "name": "Tratamientos y Aceites",
            "description": "Tratamientos nutritivos y aceites para el cabello.",
        },
    },
    "Leave-in Conditioners": {
        "fr": {
            "name": "Après-shampooing Sans Rinçage",
            "description": "Conditionneurs sans rinçage pour cheveux hydratés.",
        },
        "de": {
            "name": "Leave-in Conditioner",
            "description": "Leave-in Conditioner für hydratisiertes Haar.",
        },
        "es": {
            "name": "Acondicionadores Sin Enjuague",
            "description": "Acondicionadores sin enjuague para cabello hidratado.",
        },
    },
    "Extension Care": {
        "fr": {"name": "Soins Extensions", "description": "Produits de soins pour extensions."},
        "de": {"name": "Extension Pflege", "description": "Pflegeprodukte für Extensions."},
        "es": {
            "name": "Cuidado de Extensiones",
            "description": "Productos de cuidado para extensiones.",
        },
    },
    "Gels & Edge Control": {
        "fr": {
            "name": "Gels & Contrôle des Bordures",
            "description": "Gels et produits pour les bordures.",
        },
        "de": {
            "name": "Gels & Ansatzkontrolle",
            "description": "Gels und Produkte für die Ansatzkontrolle.",
        },
        "es": {
            "name": "Geles y Control de Bordes",
            "description": "Geles y productos para control de bordes.",
        },
    },
    "Flat Irons & Straighteners": {
        "fr": {
            "name": "Fers Plats & Lisseurs",
            "description": "Fers plats et lisseurs professionnels.",
        },
        "de": {
            "name": "Glätteisen & Haarglätter",
            "description": "Professionelle Glätteisen und Haarglätter.",
        },
        "es": {
            "name": "Planchas y Alisadores",
            "description": "Planchas y alisadores profesionales.",
        },
    },
    "Curling Wands & Irons": {
        "fr": {
            "name": "Fers à Boucler",
            "description": "Fers à boucler pour des boucles parfaites.",
        },
        "de": {"name": "Lockenstäbe & Eisen", "description": "Lockenstäbe für perfekte Locken."},
        "es": {"name": "Rizadores y Tenazas", "description": "Rizadores para rizos perfectos."},
    },
    "Clippers & Trimmers": {
        "fr": {"name": "Tondeuses & Rasoirs", "description": "Tondeuses et rasoirs de précision."},
        "de": {
            "name": "Haarschneidemaschinen & Trimmer",
            "description": "Präzisions-Haarschneidemaschinen und Trimmer.",
        },
        "es": {
            "name": "Cortadoras y Recortadoras",
            "description": "Cortadoras y recortadoras de precisión.",
        },
    },
    "False Lashes": {
        "fr": {"name": "Faux Cils", "description": "Faux cils pour un regard dramatique."},
        "de": {
            "name": "Künstliche Wimpern",
            "description": "Künstliche Wimpern für einen dramatischen Blick.",
        },
        "es": {
            "name": "Pestañas Postizas",
            "description": "Pestañas postizas para una mirada dramática.",
        },
    },
}


def main():
    print("=" * 60)
    print("Direct Category Translation Seeder")
    print("=" * 60)

    db = SessionLocal()

    try:
        # Get all locales
        locales = db.query(Locale).filter(Locale.is_enabled == True).all()
        locale_map = {loc.code: loc for loc in locales}
        print(f"\nFound locales: {list(locale_map.keys())}")

        # Get content type for category
        category_type = db.query(ContentType).filter(ContentType.api_id == "category").first()
        if not category_type:
            print("ERROR: Category content type not found!")
            return

        # Get all categories
        categories = (
            db.query(ContentEntry).filter(ContentEntry.content_type_id == category_type.id).all()
        )
        print(f"Found {len(categories)} categories")

        created_count = 0
        skipped_count = 0

        for category in categories:
            # Parse category data
            try:
                data = (
                    json.loads(category.data) if isinstance(category.data, str) else category.data
                )
            except (json.JSONDecodeError, TypeError):
                data = {}

            cat_name = data.get("name", "Unknown")
            print(f"\nProcessing: {cat_name}")

            # Check if we have translations for this category
            translations = CATEGORY_TRANSLATIONS.get(cat_name, None)

            for locale_code in ["fr", "de", "es"]:
                if locale_code not in locale_map:
                    continue

                locale = locale_map[locale_code]

                # Check if translation already exists
                existing = (
                    db.query(Translation)
                    .filter(
                        Translation.content_entry_id == category.id,
                        Translation.locale_id == locale.id,
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
                    # Fallback: use original with a note
                    translated_data = {
                        "name": data.get("name", cat_name),
                        "description": data.get("description", ""),
                    }
                    print(f"  ⚠ {locale_code}: No translation mapping, using original")
                    continue  # Skip if no translation

                # Create translation
                translation = Translation(
                    content_entry_id=category.id,
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
