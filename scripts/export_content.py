"""
Content export script for Bakalr CMS

Exports content entries to CSV or JSON format for migration and backup.
Run with: poetry run python scripts/export_content.py --format json --output data.json
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.db.session import SessionLocal
from backend.models.content import ContentEntry, ContentType
from backend.models.organization import Organization


def export_to_json(
    entries: List[ContentEntry], output_file: str, include_translations: bool = True
):
    """Export content entries to JSON format"""
    data = []

    for entry in entries:
        entry_data = {
            "id": entry.id,
            "content_type": entry.content_type.api_id,
            "content_type_name": entry.content_type.name,
            "status": entry.status,
            "data": json.loads(entry.data) if isinstance(entry.data, str) else entry.data,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
            "updated_at": entry.updated_at.isoformat() if entry.updated_at else None,
            "published_at": entry.published_at if entry.published_at else None,
            "author_id": entry.author_id,
            "organization_id": entry.organization_id,
        }

        # Include translations if requested
        if include_translations and entry.translations:
            entry_data["translations"] = []
            for trans in entry.translations:
                trans_data = {
                    "locale_code": trans.locale.code,
                    "locale_name": trans.locale.name,
                    "data": json.loads(trans.data) if isinstance(trans.data, str) else trans.data,
                    "is_published": trans.is_published,
                }
                entry_data["translations"].append(trans_data)

        data.append(entry_data)

    # Write to file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Exported {len(data)} entries to {output_file}")


def export_to_csv(entries: List[ContentEntry], output_file: str):
    """Export content entries to CSV format (flattened structure)"""
    if not entries:
        print("⚠️  No entries to export")
        return

    # Prepare rows
    rows = []
    for entry in entries:
        data_dict = json.loads(entry.data) if isinstance(entry.data, str) else entry.data

        row = {
            "id": entry.id,
            "content_type": entry.content_type.api_id,
            "content_type_name": entry.content_type.name,
            "status": entry.status,
            "created_at": entry.created_at.isoformat() if entry.created_at else "",
            "updated_at": entry.updated_at.isoformat() if entry.updated_at else "",
            "published_at": entry.published_at or "",
            "author_id": entry.author_id,
            "organization_id": entry.organization_id,
        }

        # Flatten data fields
        for key, value in data_dict.items():
            if isinstance(value, (dict, list)):
                row[f"data.{key}"] = json.dumps(value)
            else:
                row[f"data.{key}"] = value

        rows.append(row)

    # Get all unique field names
    fieldnames = set()
    for row in rows:
        fieldnames.update(row.keys())
    fieldnames = sorted(fieldnames)

    # Write to CSV
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ Exported {len(rows)} entries to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Export Bakalr CMS content to CSV or JSON")
    parser.add_argument(
        "--format", choices=["json", "csv"], default="json", help="Export format (default: json)"
    )
    parser.add_argument("--output", "-o", required=True, help="Output file path")
    parser.add_argument(
        "--content-type", "-t", help="Filter by content type API ID (e.g., blog_post, page)"
    )
    parser.add_argument("--organization", help="Filter by organization slug")
    parser.add_argument(
        "--status", choices=["draft", "published", "archived"], help="Filter by status"
    )
    parser.add_argument(
        "--include-translations",
        action="store_true",
        help="Include translations in export (JSON only)",
    )
    parser.add_argument("--limit", type=int, help="Limit number of entries to export")

    args = parser.parse_args()

    print("=" * 60)
    print("Bakalr CMS Content Export")
    print("=" * 60)

    db = SessionLocal()
    try:
        # Build query
        query = db.query(ContentEntry).join(ContentType)

        # Apply filters
        if args.content_type:
            query = query.filter(ContentType.api_id == args.content_type)
            print(f"📋 Filter: Content type = {args.content_type}")

        if args.organization:
            org = db.query(Organization).filter(Organization.slug == args.organization).first()
            if not org:
                print(f"❌ Organization '{args.organization}' not found")
                return
            query = query.filter(ContentEntry.organization_id == org.id)
            print(f"🏢 Filter: Organization = {org.name}")

        if args.status:
            query = query.filter(ContentEntry.status == args.status)
            print(f"📊 Filter: Status = {args.status}")

        if args.limit:
            query = query.limit(args.limit)
            print(f"🔢 Limit: {args.limit} entries")

        # Fetch entries
        entries = query.all()

        if not entries:
            print("\n⚠️  No entries found matching the criteria")
            return

        print(f"\n📦 Found {len(entries)} entries")

        # Export based on format
        if args.format == "json":
            export_to_json(entries, args.output, args.include_translations)
        elif args.format == "csv":
            export_to_csv(entries, args.output)

        print("\n" + "=" * 60)
        print("✅ Export completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error during export: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
