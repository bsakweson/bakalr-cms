# Multi-Tenancy & Organization Model

## Overview

Bakalr CMS uses a **SaaS-style multi-tenancy model** where each organization operates in complete isolation with its own users, content, and settings.

## Organization Creation & Ownership

### Registration Flow

1. **New User Registers** with organization name
2. **System checks**: Does organization exist?
   - ❌ **No** → Creates new organization
   - ✅ **Yes** → Requires invitation (future feature)
3. **First user** in org → **Admin role** (organization owner)
4. **Additional users** → **Viewer role** (read-only by default)

### Roles & Hierarchy

| Role | Level | Description | Auto-Assigned |
| ------ | ----- | ------------- | --------------- |
| **Admin** | 80 | Organization owner/administrator | ✅ First user only |
| **Editor** | 60 | Create, edit, publish content | ❌ Manual |
| **Author** | 40 | Create and edit own content | ❌ Manual |
| **Viewer** | 20 | Read-only access | ✅ Subsequent users |

### Current Implementation (v0.1.0)

**✅ Implemented:**
- Organization auto-creation on first signup
- Admin role assigned to organization creator
- Viewer role assigned to additional users
- On-demand role creation if roles don't exist

**⏳ Planned (v0.2.0):**
- Invitation system (owner invites employees)
- Role assignment during invitation
- Multiple admins per organization
- Organization transfer (change owner)
- Organization settings (allow public signup vs invite-only)

## Permission System

### Permission Categories

- **content**: CRUD for content entries
- **content_type**: Manage content type schemas
- **media**: Upload and manage files
- **user**: User management within organization
- **role**: Custom role creation and management
- **translation**: Multi-language content
- **webhook**: Event subscriptions
- **analytics**: View usage statistics
- **audit**: Access audit logs
- **system**: Super admin only (cross-tenant)

### Role-Permission Matrix

| Permission | Admin | Editor | Author | Viewer |
| ------------ | ----- | ------ | ------ | ------ |
| content.read | ✅ | ✅ | ✅ | ✅ |
| content.create | ✅ | ✅ | ✅ | ❌ |
| content.update | ✅ | ✅ | ✅* | ❌ |
| content.delete | ✅ | ✅ | ❌ | ❌ |
| content.publish | ✅ | ✅ | ❌ | ❌ |
| content_type.* | ✅ | ❌ | ❌ | ❌ |
| media.upload | ✅ | ✅ | ✅ | ❌ |
| user.* | ✅ | ❌ | ❌ | ❌ |
| role.* | ✅ | ❌ | ❌ | ❌ |
| webhook.* | ✅ | ❌ | ❌ | ❌ |
| analytics.view | ✅ | ✅ | ❌ | ❌ |
| audit.view | ✅ | ❌ | ❌ | ❌ |

*Author can only update own content

## User Workflows

### Scenario 1: Solo Developer

```bash
# 1. Register
POST /api/v1/auth/register
{
  "email": "dev@example.com",
  "password": "SecurePass123!",
  "full_name": "Developer Name",
  "organization_name": "My Project"
}

# Result: Organization "My Project" created
#         User assigned "admin" role automatically
#         Can create content types, upload media, manage everything
```

### Scenario 2: Team Collaboration (Current - No invites yet)

```bash
# Team Member A (First user - Owner)
POST /api/v1/auth/register
{
  "email": "owner@company.com",
  "organization_name": "Company Inc"
}
# → Gets "admin" role

# Team Member B (Second user)
POST /api/v1/auth/register
{
  "email": "employee@company.com",
  "organization_name": "Company Inc"  # Same name!
}
# → Creates SEPARATE org "Company Inc-1" (conflict)
# → Gets "admin" role in their own org
# ⚠️  PROBLEM: Can't join existing org yet!
```

### Scenario 3: Team Collaboration (Planned - With invites)

```bash
# Owner invites employee
POST /api/v1/users/invite
{
  "email": "employee@company.com",
  "role": "editor"
}
# → Sends email with invitation link

# Employee accepts invitation
POST /api/v1/users/accept-invitation
{
  "token": "invitation_token_here"
}
# → Joins existing organization
# → Gets assigned "editor" role
```

## Data Isolation

All data is scoped to organization:

- **Content Types**: `ContentType.organization_id`
- **Content Entries**: `ContentEntry.organization_id`
- **Media Files**: `Media.organization_id`
- **Translations**: `Translation.organization_id`
- **Webhooks**: `Webhook.organization_id`
- **Roles**: `Role.organization_id`
- **Users**: `User.organization_id`

**Middleware ensures** users can only access data from their organization.

## Database Schema

```sql
organizations
  ├── id, name, slug, plan_type, is_active
  └── (1-to-many) users

users
  ├── id, email, organization_id
  └── (many-to-many) roles

roles
  ├── id, name, organization_id, level
  └── (many-to-many) permissions

permissions
  └── id, name, category, description
```

## Migration from Single-Tenant

If migrating from single-tenant system:

1. Create default organization
2. Assign all users to that organization
3. Update all content with organization_id
4. Assign roles based on existing permissions

## Best Practices

### For Solo Developers

- Use one organization per project
- You're automatically admin with full access
- Create content types freely

### For Teams

- **Owner** creates organization during registration
- **Employees** need invitation system (coming in v0.2.0)
- Assign minimum necessary roles
- Use "viewer" for stakeholders who only need read access
- Upgrade to "editor" for content creators
- Keep "admin" limited to 1-2 people

### For Agencies

- Create separate organization per client
- Use multi-organization support (Phase 19)
- Switch between client organizations
- Different roles in different organizations

## Security Considerations

1. **Organization isolation** enforced at database query level
2. **Middleware validates** organization_id in JWT matches requested resources
3. **Roles scoped** to organization (can't cross organizations)
4. **Permissions checked** before every operation
5. **Audit logs** track all administrative actions

## Configuration

```bash
# .env
ALLOW_PUBLIC_REGISTRATION=true  # Anyone can create organization
MAX_USERS_PER_ORG=50            # Limit for free plan
DEFAULT_PLAN_TYPE=free          # New organizations start as "free"
```

## API Endpoints

### Organization Management

- `POST /api/v1/organizations` - Create organization (admin only)
- `GET /api/v1/organizations` - List organizations (own only)
- `GET /api/v1/organizations/{id}` - Get organization details
- `PATCH /api/v1/organizations/{id}` - Update organization (admin only)
- `DELETE /api/v1/organizations/{id}` - Delete organization (admin only)

### User Management (Within Organization)

- `GET /api/v1/users` - List organization users (admin only)
- `POST /api/v1/users/invite` - Invite user (admin only, coming soon)
- `PATCH /api/v1/users/{id}/role` - Change user role (admin only)
- `DELETE /api/v1/users/{id}` - Remove user (admin only)

### Role Management

- `GET /api/v1/roles` - List roles in organization
- `POST /api/v1/roles` - Create custom role (admin only)
- `PATCH /api/v1/roles/{id}` - Update role (admin only)
- `DELETE /api/v1/roles/{id}` - Delete role (admin only)

## Troubleshooting

### "Permission denied" after registration

**Cause**: Roles not assigned properly  
**Solution**: Check database for user roles, manually assign if needed

### Multiple organizations with same name

**Cause**: Slug collision handling  
**Solution**: System auto-appends numbers (org, org-1, org-2)

### Can't join existing organization

**Cause**: Invitation system not implemented yet  
**Workaround**: Admin manually creates user via database

## Roadmap

- ✅ **v0.1.0**: Basic multi-tenancy with auto-role assignment
- ⏳ **v0.2.0**: Invitation system, role management UI
- ⏳ **v0.3.0**: Organization transfer, multiple admins
- ⏳ **v0.4.0**: SSO integration, SCIM provisioning
