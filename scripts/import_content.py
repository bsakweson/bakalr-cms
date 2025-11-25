"""
Content import script for Bakalr CMS

Imports content entries from CSV or JSON format for migration and bulk operations.
Run with: poetry run python scripts/import_content.py --format json --input data.json
"""

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session

from backend.db.session import SessionLocal
from backend.models.content import ContentEntry, ContentType
from backend.models.organization import Organization
from backend.models.translation import Locale, Translation
from backend.models.user import User


def import_from_json(
    db: Session,
    input_file: str,
    organization_id: int,
    author_id: int,
    update_existing: bool = False,
):
    """Import content entries from JSON format"""
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    imported_count = 0
    updated_count = 0
    skipped_count = 0

    for entry_data in data:
        try:
            # Find content type
            content_type = (
                db.query(ContentType)
                .filter(
                    ContentType.api_id == entry_data["content_type"],
                    ContentType.organization_id == organization_id,
                )
                .first()
            )

            if not content_type:
                print(f"⚠️  Skipping entry: Content type '{entry_data['content_type']}' not found")
                skipped_count += 1
                continue

            # Check if entry already exists (by ID if provided)
            existing_entry = None
            if "id" in entry_data and update_existing:
                existing_entry = (
                    db.query(ContentEntry).filter(ContentEntry.id == entry_data["id"]).first()
                )

            if existing_entry:
                # Update existing entry
                existing_entry.data = json.dumps(entry_data["data"])
                existing_entry.status = entry_data.get("status", "draft")
                existing_entry.updated_at = datetime.utcnow()
                updated_count += 1
            else:
                # Create new entry
                new_entry = ContentEntry(
                    content_type_id=content_type.id,
                    organization_id=organization_id,
                    author_id=author_id,
                    data=json.dumps(entry_data["data"]),
                    status=entry_data.get("status", "draft"),
                    published_at=entry_data.get("published_at"),
                )
                db.add(new_entry)
                db.flush()

                # Import translations if present
                if "translations" in entry_data:
                    for trans_data in entry_data["translations"]:
                        locale = (
                            db.query(Locale)
                            .filter(
                                Locale.code == trans_data["locale_code"],
                                Locale.organization_id == organization_id,
                            )
                            .first()
                        )

                        if locale:
                            translation = Translation(
                                content_entry_id=new_entry.id,
                                locale_id=locale.id,
                                data=json.dumps(trans_data["data"]),
                                is_published=trans_data.get("is_published", False),
                            )
                            db.add(translation)

                imported_count += 1

            # Commit after each entry to avoid losing progress on error
            db.commit()

        except Exception as e:
            print(f"❌ Error importing entry: {e}")
            db.rollback()
            skipped_count += 1
            continue

    print("\n📊 Import Summary:")
    print(f"   ✅ Imported: {imported_count}")
    print(f"   🔄 Updated: {updated_count}")
    print(f"   ⚠️  Skipped: {skipped_count}")


def import_from_csv(
    db: Session, input_file: str, organization_id: int, author_id: int, content_type_api_id: str
):
    """Import content entries from CSV format"""
    with open(input_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Find content type
    content_type = (
        db.query(ContentType)
        .filter(
            ContentType.api_id == content_type_api_id,
            ContentType.organization_id == organization_id,
        )
        .first()
    )

    if not content_type:
        print(f"❌ Content type '{content_type_api_id}' not found")
        return

    imported_count = 0
    skipped_count = 0

    for row in rows:
        try:
            # Extract data fields (fields starting with "data.")
            data_dict = {}
            for key, value in row.items():
                if key.startswith("data."):
                    field_name = key.replace("data.", "")
                    # Try to parse JSON for complex fields
                    try:
                        data_dict[field_name] = json.loads(value) if value else None
                    except json.JSONDecodeError:
                        data_dict[field_name] = value

            # Create entry
            new_entry = ContentEntry(
                content_type_id=content_type.id,
                organization_id=organization_id,
                author_id=author_id,
                data=json.dumps(data_dict),
                status=row.get("status", "draft"),
                published_at=row.get("published_at") or None,
            )
            db.add(new_entry)
            db.commit()
            imported_count += 1

        except Exception as e:
            print(f"❌ Error importing row: {e}")
            db.rollback()
            skipped_count += 1
            continue

    print("\n📊 Import Summary:")
    print(f"   ✅ Imported: {imported_count}")
    print(f"   ⚠️  Skipped: {skipped_count}")


def main():
    parser = argparse.ArgumentParser(description="Import content to Bakalr CMS from CSV or JSON")
    parser.add_argument(
        "--format", choices=["json", "csv"], default="json", help="Import format (default: json)"
    )
    parser.add_argument("--input", "-i", required=True, help="Input file path")
    parser.add_argument(
        "--content-type", "-t", help="Content type API ID (required for CSV import)"
    )
    parser.add_argument(
        "--organization", required=True, help="Organization slug to import content into"
    )
    parser.add_argument(
        "--author-email",
        required=True,
        help="Email of the user who will be the author of imported content",
    )
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Update existing entries instead of skipping (JSON only)",
    )

    args = parser.parse_args()

    # Validate CSV requirements
    if args.format == "csv" and not args.content_type:
        print("❌ --content-type is required for CSV import")
        return

    print("=" * 60)
    print("Bakalr CMS Content Import")
    print("=" * 60)

    db = SessionLocal()
    try:
        # Find organization
        org = db.query(Organization).filter(Organization.slug == args.organization).first()
        if not org:
            print(f"❌ Organization '{args.organization}' not found")
            return

        # Find author
        author = db.query(User).filter(User.email == args.author_email).first()
        if not author:
            print(f"❌ User '{args.author_email}' not found")
            return

        print(f"🏢 Organization: {org.name}")
        print(f"👤 Author: {author.email}")
        print(f"📁 Input file: {args.input}")
        print(f"📋 Format: {args.format.upper()}")

        # Import based on format
        if args.format == "json":
            import_from_json(db, args.input, org.id, author.id, args.update_existing)
        elif args.format == "csv":
            import_from_csv(db, args.input, org.id, author.id, args.content_type)

        print("\n" + "=" * 60)
        print("✅ Import completed!")
        print("=" * 60)

    except FileNotFoundError:
        print(f"❌ File not found: {args.input}")
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON format: {e}")
    except Exception as e:
        print(f"\n❌ Error during import: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
