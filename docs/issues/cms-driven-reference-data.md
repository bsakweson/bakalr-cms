# CMS-Driven Reference Data with Multi-Language Support

**Labels:** enhancement, feature, i18n

## Overview
Implement CMS as the source of truth for reference data (departments, roles, statuses) with auto-translation support.

## Current State
- Reference data is hardcoded as Java enums in boutique-platform
- No translation support
- Adding new values requires code changes and redeployment

## Implementation Status

### ✅ CMS Side - COMPLETED

1. **Content Type Created**: `organization_reference_data` with fields:
   - `data_type`: Select (department, role, status, order_status)
   - `code`: String (e.g., 'SALES', 'ADMIN') - used by platform
   - `label`: String - default English label (auto-translated to enabled locales)
   - `description`: Text - optional description
   - `icon`: String - optional icon name
   - `color`: String - optional color hex
   - `sort_order`: Number - display ordering
   - `is_active`: Boolean - enable/disable without deletion
   - `is_system`: Boolean - system defaults cannot be deleted
   - `metadata`: JSON - additional type-specific data

2. **API Endpoints Created**: `GET /api/v1/reference-data`
   - `GET /api/v1/reference-data?type=department&locale=fr` - Get items by type with translations
   - `GET /api/v1/reference-data/types` - List available reference data types
   - `GET /api/v1/reference-data/{type}/{code}` - Get specific item
   - `POST /api/v1/reference-data` - Create new item (requires `reference_data.create`)
   - `PUT /api/v1/reference-data/{type}/{code}` - Update item (requires `reference_data.update`)
   - `DELETE /api/v1/reference-data/{type}/{code}` - Delete non-system item (requires `reference_data.delete`)
   - `GET /api/v1/reference-data/validate/{type}/{code}` - Validate a code
   - `POST /api/v1/reference-data/bulk-validate` - Validate multiple codes

3. **Seed Data Created**: Departments, roles, employment statuses, order statuses

4. **Permissions Added**:
   - `reference_data.read` - Read reference data (owner, admin, manager, api_consumer)
   - `reference_data.create` - Create reference data (owner, admin)
   - `reference_data.update` - Update reference data (owner, admin)
   - `reference_data.delete` - Delete non-system reference data (owner, admin)

5. **Webhook Support**: Use existing CMS webhook system
   - Subscribe to `content.created`, `content.updated`, `content.deleted` events
   - Filter by content_type = `organization_reference_data`

## Proposed Architecture

### Platform Side (DONE)
1. **ReferenceDataService** (`boutique-platform/common/src/main/java/.../cms/service/ReferenceDataService.java`)
   - Fetches reference data from CMS with locale support
   - In-memory caching with 5-minute TTL
   - Automatic cache refresh via @Scheduled
   - Helper methods: `getDepartments()`, `getRoles()`, `getStatuses()`, `getOrderStatuses()`
   - Validation methods: `isValidCode()`, `getValidCodes()`

2. **ReferenceDataItem DTO** (`boutique-platform/common/src/main/java/.../cms/dto/ReferenceDataItem.java`)
   - Maps CMS reference data fields
   - Includes: code, label, dataType, icon, color, sortOrder, isActive, isSystem, metadata

### Frontend Side (DONE)
1. **API Route** (`bakalr-boutique/src/app/api/reference-data/route.ts`)
   - GET: Fetch reference data with type and locale params
   - POST: Cache invalidation endpoint for webhooks
   - In-memory caching with 5-minute TTL

2. **useReferenceData Hook** (`bakalr-boutique/src/hooks/useReferenceData.ts`)
   - `useReferenceData(type?)` - Generic hook
   - `useDepartments()` - Departments shortcut
   - `useRoles()` - Roles shortcut
   - `useStatuses()` - Employment statuses
   - `useOrderStatuses()` - Order statuses
   - Helper methods: `getLabel()`, `getByCode()`, `isValidCode()`, `asOptions`

### Remaining Work
1. Update boutique-platform entities to use String instead of enum
2. Add locale selector in boutique-admin UI

## Benefits
- ✅ Business users can add/modify reference data without code changes
- ✅ Auto-translation to 100+ languages via CMS
- ✅ Consistent translations across all services
- ✅ No redeployment needed for new values
- ✅ Audit trail of changes in CMS

## Tasks
- [x] Create `reference_data` content type in CMS
- [x] Seed initial reference data (departments, roles, statuses, order_statuses)
- [x] Create CMS API endpoint for reference data with locale support
- [x] Add permissions for reference data management
- [x] Webhook infrastructure ready (use existing CMS webhooks)
- [x] Create ReferenceDataService in common module
- [x] Create ReferenceDataItem DTO in common module
- [x] Create frontend useReferenceData hook (bakalr-boutique)
- [x] Create API route /api/reference-data (bakalr-boutique)
- [ ] Update boutique-platform entities (String instead of enum)
- [ ] Add locale selector/detection in boutique-admin

## API Usage Examples

### Get departments in French
```bash
curl -X GET "http://localhost:8000/api/v1/reference-data?type=department&locale=fr" \
  -H "Authorization: Bearer <token>"
```

### Get all order statuses
```bash
curl -X GET "http://localhost:8000/api/v1/reference-data?type=order_status" \
  -H "Authorization: Bearer <token>"
```

### Validate a code
```bash
curl -X GET "http://localhost:8000/api/v1/reference-data/validate/department/SALES" \
  -H "Authorization: Bearer <token>"
```

### Bulk validate
```bash
curl -X POST "http://localhost:8000/api/v1/reference-data/bulk-validate" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '[
    {"data_type": "department", "code": "SALES"},
    {"data_type": "role", "code": "MANAGER"}
  ]'
```

## Related
- Multi-tenancy: Each organization can have custom reference data
- API Scopes: Reference data management permission
