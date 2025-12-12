#!/bin/bash
# Restore CMS database from backup
# Usage: ./restore_data.sh [backup_file]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_FILE="${1:-$SCRIPT_DIR/full_backup_20251210_184452.sql}"

echo "=== Bakalr CMS Data Restore ==="
echo "Backup file: $BACKUP_FILE"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Check if postgres container is running
if ! docker ps | grep -q bakalr-postgres; then
    echo "ERROR: bakalr-postgres container is not running"
    echo "Please start it with: docker-compose up -d postgres"
    exit 1
fi

echo ""
echo "This will restore data to the bakalr_cms database."
echo "The database schema must already exist (run migrations first)."
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "Step 1: Restoring data..."

# Copy backup file to container and restore
docker cp "$BACKUP_FILE" bakalr-postgres:/tmp/restore.sql

# Restore with triggers disabled
docker exec bakalr-postgres psql -U bakalr -d bakalr_cms -f /tmp/restore.sql

echo ""
echo "Step 2: Cleaning up..."
docker exec bakalr-postgres rm /tmp/restore.sql

echo ""
echo "=== Restore Complete ==="
echo ""
echo "Data counts after restore:"
docker exec bakalr-postgres psql -U bakalr -d bakalr_cms -c "
SELECT 'organizations' as tbl, COUNT(*) FROM organizations UNION ALL
SELECT 'users', COUNT(*) FROM users UNION ALL
SELECT 'content_types', COUNT(*) FROM content_types UNION ALL
SELECT 'content_entries', COUNT(*) FROM content_entries UNION ALL
SELECT 'translations', COUNT(*) FROM translations UNION ALL
SELECT 'media', COUNT(*) FROM media
ORDER BY 1;"
