# UUID Migration Guide

## Overview

This migration converts all Integer IDs to UUIDs (Universally Unique Identifiers) for enhanced security and scalability.

**Migration ID:** `d3836fa301f9_convert_ids_to_uuid`
**Scope:** All 24 database tables
**Breaking Change:** Yes - API and frontend updates required

## Why UUIDs?

### Security Benefits ✅

- **Prevents enumeration attacks**: Can't guess sequential IDs like `/users/1`, `/users/2`
- **No information leakage**: Doesn't reveal creation order or total count
- **Harder to exploit**: UUIDs are cryptographically random
- **OWASP recommended**: Industry best practice for public-facing APIs

### Scalability Benefits ✅

- **Distributed generation**: Can be created anywhere without DB coordination
- **Merge-friendly**: No ID conflicts when combining databases
- **Sharding-ready**: Works across multiple database instances

## What Changed

### Backend (Completed ✅)

- ✅ **Base Model**: IDMixin now uses `UUID(as_uuid=True)`
- ✅ **15 Model Files**: All foreign keys converted to UUID
- ✅ **21 API Files**: Path/query parameters accept UUID
- ✅ **Database Migration**: Created `d3836fa301f9`

### Frontend (Completed ✅)

- ✅ **11 TypeScript Files**: ID fields changed to `string`
- ⚠️ **Manual Review Needed**: parseInt(), number comparisons

### Tests (TODO)

- ❌ Update test fixtures to use UUIDs
- ❌ Update mock data
- ❌ Update factory functions

## Migration Steps

### Pre-Migration Checklist

```bash
# 1. Backup database (CRITICAL!)
docker-compose exec postgres pg_dump -U bakalr bakalr_cms > backup_before_uuid_$(date +%Y%m%d_%H%M%S).sql

# 2. Check current state
docker-compose exec postgres psql -U bakalr -d bakalr_cms -c "SELECT count(*) FROM users;"
docker-compose exec postgres psql -U bakalr -d bakalr_cms -c "SELECT count(*) FROM organizations;"

# 3. Verify no active transactions
docker-compose exec postgres psql -U bakalr -d bakalr_cms -c "SELECT * FROM pg_stat_activity WHERE datname = 'bakalr_cms';"
```

### Running the Migration

```bash
# Stop backend to prevent conflicts
docker-compose stop backend

# Run migration
docker-compose exec postgres psql -U bakalr -d bakalr_cms
# Or via alembic:
docker-compose run --rm backend alembic upgrade head

# Expected output:
# 🔄 Starting UUID migration...
# 1/8 Enabling UUID extension...
# 2/8 Adding UUID columns...
# ...
# ✅ UUID migration complete!
```

### Verification

```bash
# Check ID type changed
docker-compose exec postgres psql -U bakalr -d bakalr_cms -c "
  SELECT column_name, data_type
  FROM information_schema.columns
  WHERE table_name = 'users' AND column_name = 'id';
"
# Expected: data_type = 'uuid'

# Verify data preserved
docker-compose exec postgres psql -U bakalr -d bakalr_cms -c "SELECT count(*) FROM users;"
# Should match pre-migration count

# Check foreign keys work
docker-compose exec postgres psql -U bakalr -d bakalr_cms -c "
  SELECT u.email, o.name
  FROM users u
  JOIN organizations o ON u.organization_id = o.id
  LIMIT 5;
"
```

### Rebuild and Test

```bash
# Rebuild backend with new models
docker-compose build backend

# Start backend
docker-compose up -d backend

# Check logs
docker-compose logs backend --tail=50

# Test API
curl http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer YOUR_TOKEN"
# Should return user with UUID in 'id' field
```

## API Changes

### Before (Integer IDs)

```python
# Path parameters
@router.get("/{user_id}")
def get_user(user_id: int):
    pass

# Response
{
  "id": 1,
  "email": "user@example.com"
}
```

### After (UUID strings)

```python
# Path parameters
@router.get("/{user_id}")
def get_user(user_id: UUID):
    pass

# Response
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "email": "user@example.com"
}
```

### Frontend Updates

```typescript
// Before
interface User {
  id: number;
  email: string;
}

// After
interface User {
  id: string;  // UUID as string
  email: string;
}

// URL construction
// Before: `/users/${123}`
// After: `/users/${uuid}`
```

## Rollback Plan

⚠️ **WARNING**: Rollback requires database restore - data loss will occur.

```bash
# 1. Stop backend
docker-compose stop backend

# 2. Restore from backup
cat backup_before_uuid_YYYYMMDD_HHMMSS.sql | \
  docker-compose exec -T postgres psql -U bakalr -d bakalr_cms

# 3. Revert code changes
git revert <migration-commit-hash>

# 4. Rebuild
docker-compose build backend
docker-compose up -d backend
```

## Troubleshooting

### Issue: Migration fails with constraint errors

```bash
# Check for orphaned foreign keys
SELECT conname, conrelid::regclass, confrelid::regclass
FROM pg_constraint
WHERE contype = 'f';

# May need to drop constraints manually before migration
```

### Issue: "uuid-ossp" extension not found

```bash
# Install extension (requires superuser)
docker-compose exec postgres psql -U postgres -d bakalr_cms
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

### Issue: Frontend shows "Invalid UUID"

- Check API responses return UUID strings
- Verify frontend types updated to `string`
- Check URL routing accepts UUID format

## Testing

```bash
# Backend tests
poetry run pytest tests/ -v

# Frontend tests
cd frontend && npm test

# Integration tests
./test-e2e.sh
```

## Timeline

- **Preparation**: 30 min (backup, review)
- **Migration**: 5-10 min (depends on data size)
- **Testing**: 30 min (verify all functionality)
- **Total**: ~1 hour downtime

## Post-Migration

✅ **Verify:**
- [ ] All API endpoints return UUID strings
- [ ] Frontend displays/routes correctly
- [ ] Authentication still works
- [ ] Foreign key relationships intact
- [ ] No data loss (compare counts)

✅ **Monitor:**
- Application logs for UUID parsing errors
- Database query performance
- API response times

## Support

Issues? Check:
1. Backend logs: `docker-compose logs backend`
2. Database logs: `docker-compose logs postgres`
3. Migration output from alembic
4. GitHub Issues: [project-repo]/issues

---

**Status**: Ready for migration
**Risk Level**: High (breaking change)
**Recommended**: Test on staging environment first
