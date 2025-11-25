"""
Bulk operations CLI for Bakalr CMS

Perform bulk operations on content entries (update, delete, publish, archive).
Run with: poetry run python scripts/bulk_operations.py --help
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session

from backend.db.session import SessionLocal
from backend.models.content import ContentEntry, ContentType
from backend.models.organization import Organization


def bulk_publish(
    db: Session,
    content_type: Optional[str],
    organization_slug: str,
    status_filter: Optional[str] = None,
):
    """Publish multiple content entries"""
    query = db.query(ContentEntry).join(ContentType).join(Organization)
    query = query.filter(Organization.slug == organization_slug)

    if content_type:
        query = query.filter(ContentType.api_id == content_type)

    if status_filter:
        query = query.filter(ContentEntry.status == status_filter)
    else:
        # Only publish drafts by default
        query = query.filter(ContentEntry.status == "draft")

    entries = query.all()
    count = len(entries)

    if count == 0:
        print("⚠️  No entries found matching criteria")
        return

    print(f"📋 Found {count} entries to publish")
    confirm = input(f"❓ Confirm publishing {count} entries? (yes/no): ")

    if confirm.lower() != "yes":
        print("❌ Operation cancelled")
        return

    for entry in entries:
        entry.status = "published"
        entry.published_at = datetime.utcnow().isoformat()
        entry.updated_at = datetime.utcnow()

    db.commit()
    print(f"✅ Published {count} entries")


def bulk_archive(
    db: Session,
    content_type: Optional[str],
    organization_slug: str,
    older_than_days: Optional[int] = None,
):
    """Archive multiple content entries"""
    query = db.query(ContentEntry).join(ContentType).join(Organization)
    query = query.filter(Organization.slug == organization_slug)

    if content_type:
        query = query.filter(ContentType.api_id == content_type)

    # Only archive published entries
    query = query.filter(ContentEntry.status == "published")

    if older_than_days:
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        query = query.filter(ContentEntry.published_at < cutoff_date.isoformat())

    entries = query.all()
    count = len(entries)

    if count == 0:
        print("⚠️  No entries found matching criteria")
        return

    print(f"📋 Found {count} entries to archive")
    confirm = input(f"❓ Confirm archiving {count} entries? (yes/no): ")

    if confirm.lower() != "yes":
        print("❌ Operation cancelled")
        return

    for entry in entries:
        entry.status = "archived"
        entry.updated_at = datetime.utcnow()

    db.commit()
    print(f"✅ Archived {count} entries")


def bulk_delete(
    db: Session,
    content_type: Optional[str],
    organization_slug: str,
    status_filter: Optional[str] = None,
):
    """Delete multiple content entries (PERMANENT)"""
    query = db.query(ContentEntry).join(ContentType).join(Organization)
    query = query.filter(Organization.slug == organization_slug)

    if content_type:
        query = query.filter(ContentType.api_id == content_type)

    if status_filter:
        query = query.filter(ContentEntry.status == status_filter)

    entries = query.all()
    count = len(entries)

    if count == 0:
        print("⚠️  No entries found matching criteria")
        return

    print(f"⚠️  WARNING: This will PERMANENTLY delete {count} entries!")
    print(f"   Content type: {content_type or 'ALL'}")
    print(f"   Organization: {organization_slug}")
    print(f"   Status: {status_filter or 'ALL'}")

    confirm = input("\n❓ Type 'DELETE' to confirm: ")

    if confirm != "DELETE":
        print("❌ Operation cancelled")
        return

    for entry in entries:
        db.delete(entry)

    db.commit()
    print(f"✅ Deleted {count} entries")


def bulk_update_field(
    db: Session,
    content_type: str,
    organization_slug: str,
    field_name: str,
    field_value: str,
    status_filter: Optional[str] = None,
):
    """Update a specific field in multiple content entries"""
    query = db.query(ContentEntry).join(ContentType).join(Organization)
    query = query.filter(Organization.slug == organization_slug, ContentType.api_id == content_type)

    if status_filter:
        query = query.filter(ContentEntry.status == status_filter)

    entries = query.all()
    count = len(entries)

    if count == 0:
        print("⚠️  No entries found matching criteria")
        return

    print(f"📋 Found {count} entries to update")
    print(f"   Field: {field_name}")
    print(f"   New value: {field_value}")

    confirm = input(f"\n❓ Confirm updating {count} entries? (yes/no): ")

    if confirm.lower() != "yes":
        print("❌ Operation cancelled")
        return

    import json

    updated = 0

    for entry in entries:
        try:
            data = json.loads(entry.data) if isinstance(entry.data, str) else entry.data
            data[field_name] = field_value
            entry.data = json.dumps(data)
            entry.updated_at = datetime.utcnow()
            updated += 1
        except Exception as e:
            print(f"⚠️  Error updating entry {entry.id}: {e}")

    db.commit()
    print(f"✅ Updated {updated} entries")


def main():
    parser = argparse.ArgumentParser(description="Bulk operations for Bakalr CMS content")
    parser.add_argument(
        "operation", choices=["publish", "archive", "delete", "update"], help="Operation to perform"
    )
    parser.add_argument("--organization", "-o", required=True, help="Organization slug")
    parser.add_argument("--content-type", "-t", help="Content type API ID (e.g., blog_post, page)")
    parser.add_argument(
        "--status", choices=["draft", "published", "archived"], help="Filter by status"
    )
    parser.add_argument(
        "--older-than-days", type=int, help="For archive: only archive entries older than N days"
    )
    parser.add_argument("--field", help="For update: field name to update")
    parser.add_argument("--value", help="For update: new field value")

    args = parser.parse_args()

    # Validate update operation
    if args.operation == "update":
        if not args.content_type:
            print("❌ --content-type is required for update operation")
            return
        if not args.field or not args.value:
            print("❌ --field and --value are required for update operation")
            return

    print("=" * 60)
    print("Bakalr CMS Bulk Operations")
    print("=" * 60)
    print(f"Operation: {args.operation.upper()}")
    print(f"Organization: {args.organization}")
    if args.content_type:
        print(f"Content Type: {args.content_type}")
    if args.status:
        print(f"Status Filter: {args.status}")
    print("=" * 60)
    print()

    db = SessionLocal()
    try:
        # Verify organization exists
        org = db.query(Organization).filter(Organization.slug == args.organization).first()
        if not org:
            print(f"❌ Organization '{args.organization}' not found")
            return

        # Execute operation
        if args.operation == "publish":
            bulk_publish(db, args.content_type, args.organization, args.status)
        elif args.operation == "archive":

            bulk_archive(db, args.content_type, args.organization, args.older_than_days)
        elif args.operation == "delete":
            bulk_delete(db, args.content_type, args.organization, args.status)
        elif args.operation == "update":
            bulk_update_field(
                db, args.content_type, args.organization, args.field, args.value, args.status
            )

    except Exception as e:
        print(f"\n❌ Error during operation: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
