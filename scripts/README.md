# Bakalr CMS Scripts

This directory contains utility scripts for managing and migrating data in Bakalr CMS.

## Database Seeding

### `seed_database.py`

Initialize a fresh database with default data including permissions, roles, admin user, and sample content types.

```bash
poetry run python scripts/seed_database.py
```

**Creates:**
- 31 default permissions across 9 categories
- 5 hierarchical roles (super_admin, admin, editor, author, viewer)
- Default organization ("Bakalr CMS")
- Admin user (`admin@bakalr.cms` / `admin123`) ⚠️ **Change password immediately!**
- Default locale (English)
- 3 sample content types (Blog Post, Page, Product)

**Note:** Script is idempotent - safe to run multiple times.

---

## Content Export/Import

### `export_content.py`

Export content entries to JSON or CSV format for backup or migration.

**JSON Export (with translations):**
```bash
poetry run python scripts/export_content.py \
  --format json \
  --output backup.json \
  --include-translations
```

**CSV Export (flattened):**
```bash
poetry run python scripts/export_content.py \
  --format csv \
  --output export.csv \
  --content-type blog_post
```

**Options:**
- `--format` - Export format: `json` or `csv` (default: json)
- `--output, -o` - Output file path (required)
- `--content-type, -t` - Filter by content type API ID
- `--organization` - Filter by organization slug
- `--status` - Filter by status: draft, published, archived
- `--include-translations` - Include translations (JSON only)
- `--limit` - Limit number of entries

### `import_content.py`

Import content entries from JSON or CSV files.

**JSON Import:**
```bash
poetry run python scripts/import_content.py \
  --format json \
  --input backup.json \
  --organization bakalr-cms \
  --author-email admin@bakalr.cms \
  --update-existing
```

**CSV Import:**
```bash
poetry run python scripts/import_content.py \
  --format csv \
  --input data.csv \
  --content-type blog_post \
  --organization bakalr-cms \
  --author-email admin@bakalr.cms
```

**Options:**
- `--format` - Import format: `json` or `csv`
- `--input, -i` - Input file path (required)
- `--content-type, -t` - Content type API ID (required for CSV)
- `--organization` - Organization slug (required)
- `--author-email` - Email of content author (required)
- `--update-existing` - Update existing entries (JSON only)

---

## Bulk Operations

### `bulk_operations.py`

Perform bulk operations on multiple content entries at once.

**Publish all drafts:**
```bash
poetry run python scripts/bulk_operations.py publish \
  --organization bakalr-cms \
  --content-type blog_post \
  --status draft
```

**Archive old content:**
```bash
poetry run python scripts/bulk_operations.py archive \
  --organization bakalr-cms \
  --content-type blog_post \
  --older-than-days 365
```

**Update field across entries:**
```bash
poetry run python scripts/bulk_operations.py update \
  --organization bakalr-cms \
  --content-type blog_post \
  --field author \
  --value "New Author" \
  --status published
```

**Delete entries (PERMANENT):**
```bash
poetry run python scripts/bulk_operations.py delete \
  --organization bakalr-cms \
  --content-type blog_post \
  --status draft
```

**Operations:**
- `publish` - Change status to published and set published_at timestamp
- `archive` - Change status to archived
- `update` - Update a specific field value
- `delete` - Permanently delete entries ⚠️ **Cannot be undone!**

**Options:**
- `--organization, -o` - Organization slug (required)
- `--content-type, -t` - Content type API ID
- `--status` - Filter by status: draft, published, archived
- `--older-than-days` - For archive: only entries older than N days
- `--field` - For update: field name to update
- `--value` - For update: new field value

---

## Backup & Anonymization

### `backup_database.py`

Create database backups and anonymize user data for GDPR compliance.

**Create backup:**
```bash
poetry run python scripts/backup_database.py backup \
  --output-dir ./dumps \
  --compress \
  --keep-backups 5
```

**Anonymize user data:**
```bash
poetry run python scripts/backup_database.py anonymize \
  --exclude-emails admin@bakalr.cms \
  --anonymize-logs
```

**Backup and anonymize:**
```bash
poetry run python scripts/backup_database.py backup-and-anonymize \
  --output-dir ./dumps \
  --compress \
  --exclude-emails admin@bakalr.cms system@bakalr.cms \
  --anonymize-logs \
  --keep-backups 10
```

**Operations:**
- `backup` - Create database backup
- `anonymize` - Anonymize user data (PERMANENT)
- `backup-and-anonymize` - Backup first, then anonymize

**Options:**
- `--output-dir, -o` - Directory for backups (default: ./dumps)
- `--compress` - Compress backup with gzip
- `--exclude-emails` - Email addresses to exclude from anonymization
- `--keep-backups` - Number of recent backups to keep (default: 5)
- `--anonymize-logs` - Also anonymize audit logs (IP addresses, user agents)

**Anonymization:**
- User emails → `user_[hash]@anonymized.local`
- Names → "Anonymous User"
- Removes: bio, avatar, tokens, 2FA secrets
- Audit logs: IP addresses masked, user agents anonymized

---

## Best Practices

### Before Production

1. **Change default admin password** after running seed script
2. **Test scripts on development database** before using on production
3. **Create backups** before bulk operations or imports
3. **Verify data** after imports with spot checks

### Regular Maintenance

1. **Schedule automated backups** (daily recommended)
2. **Clean old backups** regularly to save disk space
3. **Monitor backup sizes** for growth trends
4. **Test restore process** periodically

### Data Security

1. **Encrypt backups** when storing off-site
2. **Use anonymization** for development/testing databases
3. **Exclude admin accounts** from anonymization
3. **Document all bulk operations** in audit logs

### Performance

1. **Use CSV for large datasets** (faster than JSON)
2. **Batch imports** rather than one large file
3. **Run bulk operations** during low-traffic periods
4. **Monitor database size** after imports

---

## Error Handling

All scripts include:
- ✅ Validation of required inputs
- ✅ Confirmation prompts for destructive operations
- ✅ Rollback on errors (where applicable)
- ✅ Detailed error messages
- ✅ Operation summaries with counts

---

## Troubleshooting

### "Organization not found"

Ensure the organization slug is correct. List organizations:
```bash
poetry run python -c "from backend.db.session import SessionLocal; from backend.models.organization import Organization; db = SessionLocal(); orgs = db.query(Organization).all(); [print(f'{o.slug} - {o.name}') for o in orgs]"
```

### "Content type not found"

Check content type API IDs:
```bash
poetry run python -c "from backend.db.session import SessionLocal; from backend.models.content import ContentType; db = SessionLocal(); cts = db.query(ContentType).all(); [print(f'{ct.api_id} - {ct.name}') for ct in cts]"
```

### "User not found"

List users:
```bash
poetry run python -c "from backend.db.session import SessionLocal; from backend.models.user import User; db = SessionLocal(); users = db.query(User).all(); [print(f'{u.email} (ID: {u.id})') for u in users]"
```

### Import fails with field errors

- Verify field names match content type schema
- Check JSON formatting for complex fields
- Ensure required fields have values

---

## Development

### Adding New Scripts

1. Create script in `scripts/` directory
2. Add project root to Python path
3. Use argparse for CLI arguments
4. Include confirmation for destructive operations
5. Provide detailed progress output
6. Handle errors gracefully with rollback
7. Update this README with usage examples

### Testing Scripts

```bash
# Test with development database
export DATABASE_URL="sqlite:///./test.db"
poetry run alembic upgrade head
poetry run python scripts/seed_database.py
poetry run python scripts/[your_script].py --help
```
