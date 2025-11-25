# Bakalr CMS

A modern headless CMS built with Python/FastAPI backend and Next.js frontend, featuring multi-tenancy, comprehensive RBAC, automatic translation, content templates, two-factor authentication, and advanced theming.

## Features

- 🏢 **Multi-tenancy** - Complete organization/workspace isolation with seamless tenant switching for multi-org users
- 🔐 **Comprehensive RBAC** - Custom roles, granular permissions, field-level access control, permission inheritance and role hierarchies
- 🛡️ **Two-Factor Authentication** - TOTP-based 2FA with backup codes for enhanced security
- 🌍 **Multi-language** - Automatic translation with locale detection (Google Translate/DeepL)
- 🎨 **Custom Theming** - Dark chocolate brown default theme with custom color palettes, typography, spacing
- 📋 **Content Templates** - Reusable blueprints with field defaults and configurations
- 🔍 **Advanced Search** - Meilisearch-powered full-text search with fuzzy matching, typo tolerance, highlighting, autocomplete, faceted filtering
- 📊 **SEO Optimized** - Meta tags, Open Graph, structured data, sitemaps
- 📁 **Media Management** - Upload, thumbnails, S3/local storage support, CDN optimization
- 🚀 **Real-time Updates** - WebSocket support for live collaboration
- 🔗 **Webhooks** - Event-driven integrations with HMAC signatures
- 📝 **Rich Content** - Modern content editor with dynamic field rendering, rich text (TipTap), media picker, multi-language translations, and versioning
- 📅 **Content Scheduling** - Schedule publish/unpublish with timezone support
- 🔑 **API Keys** - Programmatic access with permission scoping
- 🚦 **Rate Limiting** - Per-user, per-tenant, per-IP rate limits
- 📖 **Interactive API Docs** - OpenAPI with real-time testing (131+ endpoints)
- 🔄 **GraphQL API** - Flexible query interface with 8 queries, 2 mutations, JWT auth

## Tech Stack

### Backend

- **Python 3.11+** with **FastAPI**
- **Poetry** for dependency management
- **PostgreSQL** database
- **SQLAlchemy** ORM
- **Redis** for caching and pub/sub
- **Celery** for background tasks
- **Alembic** for database migrations
- **AWS S3/boto3** for cloud storage (optional)

### Frontend

- **Next.js 14+** with App Router
- **TypeScript**
- **TailwindCSS** for styling
- **shadcn/ui** component library
- **Tiptap/Lexical** rich text editor

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (LTS)
- PostgreSQL 14+ (or SQLite for development)
- Redis 6+
- Poetry

### Backend Setup

```bash
# Install dependencies
poetry install

# Copy environment file
cp .env.example .env

# Edit .env with your configuration
# DATABASE_URL, REDIS_URL, SECRET_KEY, etc.

# Run migrations
poetry run alembic upgrade head

# Run the development server
poetry run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env.local

# Edit .env.local with your backend API URL
# NEXT_PUBLIC_API_URL=http://localhost:8000

# Run the development server
npm run dev
```

The frontend will be available at `http://localhost:3000`

### First Steps

1. Open `http://localhost:3000` in your browser
2. Click "Get Started" to create your account and organization
3. Log in with your credentials
4. Explore the admin dashboard at `http://localhost:3000/dashboard`

### API Documentation

- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`
- OpenAPI JSON: `http://localhost:8000/api/openapi.json`
- GraphQL Playground: `http://localhost:8000/api/v1/graphql` (debug mode only)

## Project Structure

```text
bakalr-cms/
├── backend/
│   ├── api/               # API endpoints
│   │   ├── auth.py        # Authentication
│   │   ├── content.py     # Content management
│   │   ├── translation.py # Translation & locales
│   │   ├── seo.py         # SEO metadata & sitemaps
│   │   └── media.py       # Media file management
│   ├── core/              # Core configuration
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── storage.py
│   │   ├── seo_utils.py
│   │   ├── media_utils.py
│   │   └── translation_service.py
│   ├── models/            # Database models
│   │   ├── user.py
│   │   ├── content.py
│   │   ├── translation.py
│   │   └── media.py
│   ├── db/                # Database config
│   └── main.py            # FastAPI app
├── frontend/              # Next.js app (Phase 10)
├── tests/                 # Test files
│   ├── test_auth.py
│   ├── test_content.py
│   ├── test_translation.py
│   └── test_seo.py
├── alembic/               # Database migrations
├── .env.example           # Environment template
├── pyproject.toml         # Python dependencies
├── IMPLEMENTATION_PLAN.md # Development roadmap
├── STORAGE_CONFIG.md      # Storage configuration guide
└── README.md
```

## Development

### Run Tests

```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run python test_auth.py
poetry run python test_content.py
poetry run python test_translation.py
poetry run python test_seo.py
```

## Storage & Media Management

### Storage Architecture

The media management system supports pluggable storage backends with automatic switching via configuration:

```mermaid
graph TD
    A[Media API] --> B{get_storage_backend}
    B --> C[LocalStorageBackend]
    B --> D[S3StorageBackend]
    C --> E[Local Filesystem]
    D --> F[AWS S3]
    D --> G[S3-Compatible Services]
    G --> H[MinIO]
    G --> I[DigitalOcean Spaces]
    G --> J[Wasabi]
```

### Storage Backend Selection

Configure via the `STORAGE_BACKEND` environment variable:

**Local Storage (Default):**

```bash
STORAGE_BACKEND=local
UPLOAD_DIR=uploads
```

**AWS S3:**

```bash
STORAGE_BACKEND=s3
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name
S3_USE_SSL=true
```

**S3-Compatible Services:**

```bash
STORAGE_BACKEND=s3
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket
S3_ENDPOINT_URL=https://your-s3-service.com
S3_USE_SSL=true
```

**CDN Integration:**

```bash
STORAGE_BACKEND=s3
S3_PUBLIC_URL=https://cdn.yourdomain.com
# ... other S3 settings
```

### File Upload Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Storage
    participant LocalFS
    participant S3
    participant DB

    Client->>API: POST /media/upload
    API->>API: Validate file (type, size)
    API->>Storage: get_storage_backend()
    
    alt Local Storage
        Storage->>LocalFS: save_file()
        LocalFS-->>Storage: file_path
    else S3 Storage
        Storage->>S3: put_object()
        S3-->>Storage: s3_url
    end
    
    Storage-->>API: file_url
    API->>DB: Create media record
    DB-->>API: media_id
    API-->>Client: {id, url, metadata}
```

### File Download Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Storage
    participant LocalFS
    participant S3

    Client->>API: GET /media/files/{filename}
    API->>API: Find media record
    API->>Storage: get_storage_backend()
    
    alt Local Storage
        Storage->>LocalFS: Read file
        LocalFS-->>API: File content
        API-->>Client: FileResponse
    else S3 Storage
        Storage->>S3: get_file_url()
        S3-->>Storage: Presigned URL
        API-->>Client: RedirectResponse to S3
        Client->>S3: Direct download
    end
```

### Storage Features Comparison

| Feature | Local Storage | S3 Storage |
|---------|---------------|------------|
| File Upload | ✅ Direct | ✅ Via boto3 |
| File Download | ✅ Direct serve | ✅ Redirect to S3 |
| File Deletion | ✅ | ✅ |
| Thumbnail Generation | ✅ | ✅ (temp download) |
| Image Dimensions | ✅ | ⚠️ Skipped |
| CDN Support | ❌ | ✅ |
| Scalability | Limited | High |
| Cost | None | Usage-based |
| Backup | Manual | S3 versioning |

### IAM Permissions for AWS S3

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject",
                "s3:ListBucket",
                "s3:HeadObject"
            ],
            "Resource": [
                "arn:aws:s3:::your-bucket-name",
                "arn:aws:s3:::your-bucket-name/*"
            ]
        }
    ]
}
```

### S3 Bucket Configuration

**CORS (for browser access):**

```json
[
    {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
        "AllowedOrigins": ["*"],
        "ExposeHeaders": ["ETag"]
    }
]
```

**Public Read Policy:**

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::your-bucket-name/*"
        }
    ]
}
```

### Storage Backend Implementation

The system uses a pluggable architecture defined in `backend/core/storage.py`:

**StorageBackend Interface:**

```python
class StorageBackend(ABC):
    @abstractmethod
    def save_file(self, file_content: bytes, file_path: str) -> str:
        """Save file and return URL"""
        pass
    
    @abstractmethod
    def delete_file(self, file_path: str) -> bool:
        """Delete file from storage"""
        pass
    
    @abstractmethod
    def get_file_url(self, file_path: str) -> str:
        """Get public URL for file"""
        pass
    
    @abstractmethod
    def file_exists(self, file_path: str) -> bool:
        """Check if file exists"""
        pass
```

**Usage in Code:**

```python
from backend.core.storage import get_storage_backend

# Get configured storage backend
storage = get_storage_backend()

# Save file (works with local or S3)
file_url = storage.save_file(file_content, "path/to/file.jpg")

# Delete file
storage.delete_file("path/to/file.jpg")

# Check existence
if storage.file_exists("path/to/file.jpg"):
    print("File exists")
```

### Kubernetes Deployment

All storage configuration is externalized via environment variables, making it Kubernetes-ready:

```yaml
# ConfigMap example
env:
  - name: STORAGE_BACKEND
    value: "s3"
  - name: S3_BUCKET_NAME
    value: "bakalr-cms-media"
  - name: AWS_REGION
    value: "us-east-1"

# Secret example
env:
  - name: AWS_ACCESS_KEY_ID
    valueFrom:
      secretKeyRef:
        name: aws-credentials
        key: access-key-id
  - name: AWS_SECRET_ACCESS_KEY
    valueFrom:
      secretKeyRef:
        name: aws-credentials
        key: secret-access-key
```

### Testing Storage

Run storage backend tests:

```bash
# Test storage configuration
poetry run python test_storage.py

# Upload test file
curl -X POST "http://localhost:8000/api/v1/media/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test-image.jpg"

# Verify in S3 (if using S3)
aws s3 ls s3://your-bucket-name/
```

### Migration Between Storage Backends

To migrate from local to S3:

1. **Backup** existing files
2. **Update** environment variables to S3
3. **Upload** files to S3 bucket
4. **Update** database records with new URLs
5. **Restart** application

### Troubleshooting

**S3 Connection Issues:**

```bash
# Test AWS credentials
aws s3 ls s3://your-bucket-name

# Check connectivity
aws s3api head-bucket --bucket your-bucket-name
```

**Permission Issues:**

- Verify IAM credentials have required permissions
- Check bucket policy allows operations
- Ensure bucket exists in specified region

**File Not Found:**

- Local: Check `UPLOAD_DIR` path and permissions
- S3: Verify bucket name, region, and file paths in database

### Code Formatting

```bash
poetry run black backend/
poetry run ruff check backend/
```

### Type Checking

```bash
poetry run mypy backend/
```

## Performance & Optimization

### Caching Strategy

The CMS implements a comprehensive caching strategy using Redis:

#### Response Caching

- **ETag Support**: Generates MD5 hash of response content for efficient cache validation
- **304 Not Modified**: Reduces bandwidth with If-None-Match header support
- **Cache Headers**: Automatic X-Cache headers (HIT, MISS, HIT-304) for debugging
- **Configurable TTL**: Default 300s response cache, customizable per endpoint
- **Selective Caching**: Only caches GET requests by default, with path exclusions

#### Cache Invalidation

Cache invalidation patterns ensure data consistency:

```python
# Content updates invalidate related caches
await invalidate_cache_pattern(f"content:entry:{tenant_id}:{entry_id}:*")
await invalidate_cache_pattern(f"content:list:{tenant_id}:*")
await invalidate_cache_pattern(f"seo:*:{tenant_id}:*")
```

**Invalidation Triggers**:

- Content update/delete → Content, translation, and SEO caches
- Content publish → Content list and sitemap caches
- Translation update → Translation and content caches
- Media upload/delete → Media file and stats caches

#### CDN Cache Headers

Media files served with optimized cache headers:

- **Immutable files**: `Cache-Control: public, max-age=31536000` (1 year)
- **S3 redirects**: `Cache-Control: public, max-age=3600` (1 hour)
- Compatible with CloudFront, CloudFlare, Fastly, etc.

#### Cache Configuration

```bash
# Environment variables
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=10
CACHE_DEFAULT_TTL=300  # 5 minutes
```

### Rate Limiting

Multi-tier rate limiting with Redis backend:

#### Rate Limit Tiers

| Tier | Limits | Use Case |
|------|--------|----------|
| Anonymous | 100/hour, 10/minute | Unauthenticated requests |
| Authenticated | 1000/hour, 100/minute | Regular users |
| API Key Free | 5000/hour, 100/minute | Free tier API access |
| API Key Pro | 50000/hour, 500/minute | Pro tier API access |
| Enterprise | Unlimited | Enterprise customers |
| Expensive Ops | 50/hour | Uploads, translations, searches |

#### Rate Limit Headers

All responses include rate limit information:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 847
X-RateLimit-Reset: 1700000000
```

#### Per-Endpoint Limits

Custom rate limits for specific operations:

```python
@router.post("/upload")
@rate_limit("50/hour")  # Upload-specific limit
async def upload_media():
    pass
```

#### Identifier Resolution

Rate limits identified by (in priority order):

1. API Key (from X-API-Key header)
2. User ID (from JWT token)
3. IP Address (fallback)

#### Rate Limit Configuration

```bash
# Environment variables
REDIS_URL=redis://localhost:6379/0
RATE_LIMIT_ENABLED=true
RATE_LIMIT_STORAGE_URL=redis://localhost:6379/1
```

### Cache Patterns

Centralized cache key patterns for all resources:

```python
# Content
content:entry:{tenant_id}:{entry_id}:{version}
content:list:{tenant_id}:{content_type}:{filters}
content:type:{tenant_id}:{type_id}

# Translations
translation:{tenant_id}:{entry_id}:{locale}
translation:list:{tenant_id}:{locale}

# Media
media:file:{tenant_id}:{media_id}
media:stats:{tenant_id}

# SEO
seo:meta:{tenant_id}:{entry_id}
seo:sitemap:{tenant_id}:{locale}

# User
user:profile:{user_id}
user:permissions:{user_id}:{tenant_id}
```

## Webhooks & Events

The CMS includes a comprehensive webhook system for event-driven integrations.

### Webhook Features

- **Event Types**: Content, media, translation, user, and organization events
- **HMAC Signatures**: Secure payload verification with HMAC-SHA256
- **Automatic Retries**: Exponential backoff (60s, 120s, 240s, ...)
- **Delivery Tracking**: Full logging of attempts, responses, and errors
- **Custom Headers**: Support for authentication headers
- **Testing**: Built-in webhook testing with custom payloads

### Available Events

```text
content.created       - Content entry created
content.updated       - Content entry updated
content.deleted       - Content entry deleted
content.published     - Content entry published
content.unpublished   - Content entry unpublished

media.uploaded        - Media file uploaded
media.updated         - Media file metadata updated
media.deleted         - Media file deleted

translation.created   - Translation created
translation.updated   - Translation updated

user.created          - User account created
user.updated          - User account updated
user.deleted          - User account deleted

organization.created  - Organization created
organization.updated  - Organization updated
```

### Creating a Webhook

```bash
POST /api/webhooks
Content-Type: application/json
Authorization: Bearer {token}

{
  "name": "My Webhook",
  "description": "Notify on content changes",
  "url": "https://example.com/webhooks/cms",
  "events": ["content.created", "content.updated", "content.published"],
  "headers": {
    "Authorization": "Bearer my-secret-token"
  },
  "max_retries": 3,
  "retry_delay": 60
}

Response:
{
  "id": 1,
  "secret": "abc123xyz789...",
  "message": "Store this secret securely. It will not be shown again."
}
```

### Verifying Webhook Signatures

All webhook requests include an `X-Webhook-Signature` header with HMAC-SHA256 signature:

```python
import hmac
import hashlib

def verify_webhook(payload: bytes, signature: str, secret: str) -> bool:
    """Verify webhook signature"""
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)

# Usage
payload = request.body  # Raw request body
signature = request.headers["X-Webhook-Signature"]
secret = "your-webhook-secret"

if verify_webhook(payload, signature, secret):
    # Process webhook
    pass
```

### Webhook Payload Structure

```json
{
  "event_id": "evt_1234567890abcdef",
  "event_type": "content.created",
  "timestamp": "2025-11-24T12:00:00Z",
  "organization_id": 1,
  "data": {
    "content_id": 42,
    "type": "blog_post",
    "title": "New Blog Post",
    "status": "draft",
    "author_id": 1
  }
}
```

### Webhook Headers

Each webhook request includes:

- `X-Webhook-Signature`: HMAC-SHA256 signature
- `X-Webhook-ID`: Webhook ID
- `X-Event-Type`: Event type
- `X-Event-ID`: Unique event identifier
- `X-Delivery-ID`: Delivery attempt ID
- `X-Delivery-Attempt`: Attempt number (1, 2, 3, ...)
- `Content-Type`: application/json
- `User-Agent`: Bakalr-CMS-Webhook/1.0

### Testing Webhooks

```bash
POST /api/webhooks/{webhook_id}/test
Content-Type: application/json
Authorization: Bearer {token}

{
  "event_type": "content.created",
  "custom_payload": {
    "test": true,
    "message": "This is a test"
  }
}
```

### Managing Deliveries

```bash
# List delivery attempts
GET /api/webhooks/{webhook_id}/deliveries

# Get delivery details
GET /api/webhooks/{webhook_id}/deliveries/{delivery_id}

# Retry failed delivery
POST /api/webhooks/{webhook_id}/deliveries/{delivery_id}/retry
```

### Retry Behavior

- **Initial attempt**: Immediate delivery
- **Retry 1**: After 60 seconds
- **Retry 2**: After 120 seconds (2 minutes)
- **Retry 3**: After 240 seconds (4 minutes)
- **Max retries**: Configurable (default 3)

Deliveries are retried only for:

- Network errors (timeout, connection refused)
- HTTP 5xx server errors
- HTTP 429 (rate limited)

Successful responses (2xx) and client errors (4xx, except 429) do not trigger retries.

## Multi-Organization & Tenant Switching

Users can belong to multiple organizations and seamlessly switch between them with different roles in each organization.

### Use Cases

- **Agencies**: Manage multiple client organizations
- **Contractors**: Work for multiple companies with different permissions
- **Consultants**: Access multiple project workspaces
- **Multi-brand companies**: Manage separate brand workspaces

### Tenant Switching Features

- Users can be members of multiple organizations
- Different roles per organization (e.g., Admin in Org A, Editor in Org B)
- Seamless switching with JWT token refresh
- Set default organization for automatic login
- Invite users to your organization
- Remove users from organization (requires permissions)

### API Endpoints

#### List User's Organizations

```bash
GET /api/v1/tenant/organizations
Authorization: Bearer {token}

Response:
{
  "current_organization_id": 1,
  "organizations": [
    {
      "organization_id": 1,
      "organization_name": "Agency A",
      "organization_slug": "agency-a",
      "is_default": true,
      "is_active": true,
      "roles": ["admin", "editor"],
      "joined_at": "2025-01-01T00:00:00Z"
    },
    {
      "organization_id": 2,
      "organization_name": "Client B",
      "organization_slug": "client-b",
      "is_default": false,
      "is_active": true,
      "roles": ["viewer"],
      "joined_at": "2025-02-15T10:30:00Z"
    }
  ],
  "total": 2
}
```

#### Switch to Different Organization

```bash
POST /api/v1/tenant/switch
Authorization: Bearer {token}
Content-Type: application/json

{
  "organization_id": 2
}

Response:
{
  "access_token": "new_jwt_token...",
  "refresh_token": "new_refresh_token...",
  "token_type": "bearer",
  "organization_id": 2,
  "organization_name": "Client B",
  "roles": ["viewer"],
  "message": "Successfully switched to Client B"
}
```

After switching, use the new tokens for all subsequent requests. All data will be scoped to the new organization.

#### Set Default Organization

```bash
POST /api/v1/tenant/set-default
Authorization: Bearer {token}
Content-Type: application/json

{
  "organization_id": 2
}

Response:
{
  "organization_id": 2,
  "organization_name": "Client B",
  "is_default": true,
  "message": "Client B is now your default organization"
}
```

#### Invite User to Organization

```bash
POST /api/v1/tenant/invite
Authorization: Bearer {token}
Content-Type: application/json

{
  "email": "user@example.com",
  "role_names": ["editor", "contributor"]
}

Response:
{
  "user_id": 42,
  "email": "user@example.com",
  "organization_id": 1,
  "organization_name": "Agency A",
  "invitation_sent": true,
  "message": "user@example.com has been added to Agency A"
}
```

**Requirements**: 'users.manage' permission in current organization

#### Remove User from Organization

```bash
DELETE /api/v1/tenant/remove/{user_id}
Authorization: Bearer {token}

Response:
{
  "message": "User user@example.com has been removed from the organization",
  "user_id": 42,
  "organization_id": 1
}
```

**Requirements**:

- 'users.manage' permission
- Cannot remove yourself
- Cannot remove the last admin

### Multi-Organization Workflow Example

1. **Designer logs in** → Starts in default organization (Agency A)
2. **Check organizations** → `GET /tenant/organizations` (sees 3 organizations)
3. **Switch to Client B** → `POST /tenant/switch` with org_id=2
4. **Receive new tokens** → Use new JWT for all requests
5. **Work on Client B** → All API calls scoped to Client B
6. **Switch back to Agency A** → `POST /tenant/switch` with org_id=1
7. **Set default org** → `POST /tenant/set-default` for auto-selection on next login

### Security & Isolation

- Organization membership verified before switching
- Inactive organizations cannot be switched to
- JWT contains `org_id` for automatic tenant filtering
- All database queries automatically filtered by organization_id
- Cross-tenant data access prevented by middleware
- Role assignments scoped to organization
- Invitation system prevents unauthorized access

## Testing

All major features have comprehensive test coverage. Tests are written using pytest with async support.

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=backend --cov-report=html

# Run specific test suite
poetry run pytest test_auth.py -v
poetry run pytest test_content.py -v
poetry run pytest test_translation.py -v
poetry run pytest test_seo.py -v
poetry run pytest test_storage.py -v
poetry run pytest test_cache.py -v        # Requires Redis
poetry run pytest test_rate_limit.py -v   # Requires Redis
```

### Redis Requirement

Cache and rate limit tests require a running Redis instance:

```bash
# macOS with Homebrew
brew services start redis

# Linux
sudo systemctl start redis

# Docker
docker run -d -p 6379:6379 redis:latest
```

## Current Status

✅ **Phases 1-13 Complete + Phase 6.5** (including Phase 11 Frontend, Phase 12 Notifications, Phase 6.5 Advanced Search)

### Backend Features

- **Database**: 27 tables with full multi-tenancy support
- **Backend API**: 152+ REST endpoints across 19 modules
- **GraphQL API**: Flexible query interface at /api/v1/graphql with 8 queries, 2 mutations
- **Authentication**: JWT with refresh tokens, 2FA (TOTP), API keys, tenant switching
- **Authorization**: Comprehensive RBAC with field-level permissions, role hierarchies
- **Content Management**: Full CRUD with versioning, relationships, templates, scheduling
- **Translation**: Auto-translation to 100+ locales with Google Translate/DeepL
- **SEO**: Metadata, sitemaps, structured data, Open Graph, Twitter Cards
- **Media**: Upload, thumbnails, local/S3 storage, CDN optimization
- **Search**: Meilisearch with full-text search, fuzzy matching, typo tolerance, highlighting, autocomplete, faceted filtering
- **Caching**: Redis with ETags, response caching, cache warming
- **Rate Limiting**: SlowAPI with per-user/tenant/IP limits
- **Webhooks**: Event-driven with HMAC signatures, retries, delivery tracking
- **Notifications**: In-app notifications with email delivery (13 endpoints)
- **Email System**: FastAPI-Mail with 4 templates, delivery tracking, retry logic
- **Theming**: Custom themes with Dark Chocolate default, CSS variables export
- **Testing**: 51+ tests across 6 comprehensive test suites

### Frontend Application

- **Framework**: Next.js 16.0.4 with App Router and TypeScript
- **Styling**: TailwindCSS with dark chocolate brown theme (#3D2817)
- **UI Components**: shadcn/ui (12 components: button, card, input, label, select, textarea, dropdown-menu, sheet, dialog, avatar, badge, separator)
- **Authentication**: JWT-based with automatic token refresh, protected routes
- **API Clients**: Axios for REST (with interceptors), Fetch for GraphQL
- **State Management**: React Context (AuthProvider for user state)
- **Pages**: Landing page, login, register, admin dashboard with sidebar navigation
- **Features**: Responsive layout, dark/light mode, user profile dropdown, organization context

## GraphQL API

The CMS provides a GraphQL interface alongside the REST API for flexible querying.

### GraphQL Endpoint

- **URL**: `http://localhost:8000/api/v1/graphql`
- **Playground**: Available in debug mode at same URL
- **Authentication**: JWT token via `Authorization: Bearer <token>` header
- **Organization Scoping**: All queries automatically filtered by user's organization

### Example Queries

**Get content entries with nested data:**

```graphql
query GetBlogPosts {
  contentEntries(
    page: 1,
    per_page: 10,
    status: "published",
    content_type_slug: "blog_post"
  ) {
    items {
      id
      slug
      status
      content_data
      published_at
      author {
        email
        full_name
      }
      content_type {
        name
        slug
        fields
      }
    }
    pagination {
      total
      page
      total_pages
      has_next
      has_prev
    }
  }
}
```

**Get current user profile:**

```graphql
query Me {
  me {
    id
    email
    full_name
    organization {
      name
      slug
    }
  }
}
```

**List media files:**

```graphql
query GetMedia {
  media(page: 1, per_page: 20) {
    items {
      id
      filename
      content_type
      public_url
      alt_text
      width
      height
      uploaded_by {
        email
      }
    }
    pagination {
      total
      has_next
    }
  }
}
```

### Example Mutations

**Publish content entry:**

```graphql
mutation PublishPost {
  publishContent(id: 42) {
    id
    slug
    status
    published_at
  }
}
```

**Unpublish content entry:**

```graphql
mutation UnpublishPost {
  unpublishContent(id: 42) {
    id
    status
  }
}
```

### Available Queries

- `contentEntry(id: Int!)` - Get single content entry
- `contentEntries(page, per_page, status, content_type_slug)` - List content with filters
- `contentTypes()` - List all content types
- `media(page, per_page)` - List media files
- `me()` - Current authenticated user
- `locales()` - Enabled locales
- `themes()` - Organization themes
- `contentTemplates(published_only)` - List content templates

### Available Mutations

- `publishContent(id: Int!)` - Publish content (requires `content.publish` permission)
- `unpublishContent(id: Int!)` - Unpublish content (requires `content.update` permission)

### Benefits vs REST API

- **Flexible Data Fetching**: Request only the fields you need
- **Nested Relationships**: Get related data in a single query
- **Reduced Over-fetching**: Avoid unnecessary data transfer
- **Strong Typing**: Type-safe queries with validation
- **Self-Documenting**: Introspection for schema exploration
- **Developer Experience**: GraphiQL playground for testing

## Implementation Details

### Content Templates & Blueprints

Content templates provide reusable structures for rapid content creation with predefined field defaults and configurations.

#### Template Key Features

- **Field Defaults**: Pre-fill common values (status=draft, author=current_user)
- **Field Configuration**: Validation rules, help text, editor preferences per field
- **Content Structure**: Define sections, layouts, required vs optional fields
- **Template Categories**: Group templates (blog, product, landing-page)
- **Tag-based Discovery**: Search templates by tags
- **Usage Tracking**: Monitor template popularity and applications
- **Smart Merging**: User overrides take precedence over template defaults

#### Template Use Cases

- Blog post templates (Standard Article, Tutorial, News, Interview)
- Product page templates (Physical Product, Digital Product, Service)
- Landing page templates (Sales, Lead Generation, Event Registration)
- Marketing templates (Email Campaign, Social Media Post)
- Documentation templates (API Reference, How-to Guide, FAQ)

#### Template Configuration

```bash
CONTENT_TEMPLATES_ENABLED=true
MAX_TEMPLATES_PER_TYPE=50
```

### Two-Factor Authentication (2FA)

TOTP-based two-factor authentication with backup codes for enhanced account security.

#### 2FA Features

- **TOTP Standard**: RFC 6238 compliant, 30-second validity window
- **Authenticator Apps**: Compatible with Google Authenticator, Microsoft Authenticator, Authy
- **QR Code Provisioning**: Easy setup by scanning QR code
- **Backup Codes**: 10 one-time recovery codes (bcrypt-hashed)
- **Role-based Enforcement**: Optional mandatory 2FA for admin roles
- **Clock Drift Tolerance**: ±1 window for time synchronization issues

#### 2FA Configuration

```bash
TWO_FACTOR_ENABLED=true
TWO_FACTOR_ISSUER_NAME="Bakalr CMS"
TWO_FACTOR_CODE_VALIDITY_SECONDS=30
TWO_FACTOR_BACKUP_CODES_COUNT=10
TWO_FACTOR_ENFORCE_FOR_ADMINS=false
```

#### 2FA User Workflow

1. Call `/auth/2fa/enable` → Receive QR code, secret, and 10 backup codes
2. Scan QR code with authenticator app
3. Call `/auth/2fa/verify-setup` with code from app → 2FA activated
4. Login now requires TOTP code verification
5. Lost device → Use backup codes via `/auth/2fa/verify-backup`
6. Call `/auth/2fa/backup-codes/regenerate` → New codes issued (old invalidated)

### Tenant Switching for Multi-Organization Users

Users can belong to multiple organizations and seamlessly switch between them with different roles in each.

#### Tenant Database Schema

**UserOrganization** many-to-many association table:

- `user_id`, `organization_id` - Relationships with CASCADE delete
- `is_active` - Active membership status
- `is_default` - Default organization for login
- `role_context` - JSON field for per-organization role assignments
- `invited_by` - Invitation tracking
- `invitation_accepted_at` - Invitation acceptance timestamp
- Unique constraint on (user_id, organization_id)
- Indexes on foreign keys for performance

#### Multi-Tenant Capabilities

- **Multiple Organizations**: Users belong to multiple orgs simultaneously
- **Seamless Switching**: JWT token refresh on organization switch
- **Per-Organization Roles**: Different permissions in each organization
- **Default Organization**: Automatic organization on login
- **Invitation System**: Invite users with role assignments
- **Organization Management**: Add/remove users (requires `users.manage` permission)
- **Backward Compatible**: Single-org users still supported

#### Tenant Security & Isolation

- Organization membership verified before switching
- Inactive organizations cannot be switched to
- JWT contains `org_id` for automatic tenant filtering
- Cross-tenant data access prevented by middleware
- Role assignments scoped to organization
- Prevents self-removal and unauthorized access

#### Tenant Switching Use Cases

**Agency Managing Multiple Clients**:
Designer works for Agency A (Admin), Client B (Editor), Client C (Viewer)

- Switches between clients seamlessly
- Different permissions per client
- Manages multiple projects efficiently

**Contractor for Multiple Companies**:
Developer works for Company X (Admin), Company Y (Contributor)

- Access different codebases per company
- Different development permissions
- Single account across all companies

**Multi-Brand Company**:
Manager oversees Brand A (Admin), Brand B (Admin), Brand C (Editor)

- Switch between brand workspaces
- Consistent brand management
- Centralized account management

#### Tenant Authentication Flow

1. User logs in → JWT contains current `organization_id`
2. User calls `GET /tenant/organizations` → See all accessible orgs
3. User calls `POST /tenant/switch` with target `org_id` → New JWT issued
4. All subsequent API calls use new organization context
5. User can set default org for automatic selection on next login

## Documentation

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for the complete implementation roadmap and progress tracking.

## Content Editor Features

The admin dashboard includes a powerful content editor with advanced features for managing dynamic content.

### Rich Text Editor (TipTap)

**Field Types**: `richtext`, `wysiwyg`, `html`

WYSIWYG editor with comprehensive formatting toolbar:

- **Text Formatting**: Bold, Italic, Headings (H1, H2)
- **Lists**: Bullet lists, Numbered lists
- **Blockquotes**: For quotations
- **Links**: Add hyperlinks
- **Images**: Insert via URL or media picker
- **History**: Undo/Redo support
- **Output**: Clean semantic HTML

**Example Schema**:

```json
{
  "body": {
    "type": "richtext",
    "label": "Article Body",
    "description": "The main content of the article",
    "required": true
  }
}
```

### Media Picker

**Field Types**: `image`, `file`, `media`

Visual media browser with upload capability:

- Browse existing media files in grid view
- Upload new files via drag-and-drop or button
- Search by filename
- Filter by type (images, videos, audio, documents)
- Pagination for large libraries
- Image thumbnails and file information
- Automatic URL population

**Usage**:

1. Click "Browse" button next to image/file field
2. Select existing file or upload new one
3. Click "Select" to use the chosen file
4. URL auto-populated with preview (for images)

**Example Schema**:

```json
{
  "featured_image": {
    "type": "image",
    "label": "Featured Image",
    "description": "Main article image"
  }
}
```

### Multi-language Translation Tabs

**Requirements**: Create locales in organization settings first

Translation interface with tab-based navigation:

- Default content tab + one tab per enabled locale
- All field types supported (including rich text and media)
- Translation forms with fallback to default content
- Auto-save translations alongside content
- Visual indicators (Globe icon)

**Workflow**:

1. Create content in "Default Content" tab
2. Switch to locale tab (e.g., "Español", "Français")
3. Fill in translated versions of fields
4. Leave fields empty to use default content
5. Save to store all translations together

### Content Type Builder

Visual schema builder for creating content types without writing JSON:

- **12 Field Types**: Text, Textarea, Rich Text, Number, Email, URL, Select, Boolean, Image, File, Date, DateTime
- **Visual Interface**: Click field type cards to add fields
- **Field Configuration**: Dynamic property editor for each field type
- **Field Reordering**: Up/down arrows to change field order
- **Schema Validation**: Duplicate key detection, required fields check
- **Edit Existing**: Load and modify existing content type schemas

**Supported Field Types**:

- `text` - Single-line text input
- `textarea` - Multi-line plain text
- `richtext`/`wysiwyg`/`html` - TipTap WYSIWYG editor
- `number` - Numeric input with min/max validation
- `email` - Email with validation
- `url` - URL with validation
- `select` - Dropdown with custom options
- `boolean` - Checkbox
- `image`/`file`/`media` - Media picker integration
- `date` - Date picker
- `datetime` - Date and time picker

**Example: Creating a Blog Post Content Type**:

1. Navigate to Content Types → Create Content Type
2. Enter name: "Blog Post" (auto-generates slug: `blog_post`)
3. Add fields:
   - Title (text, required)
   - Excerpt (textarea)
   - Body (richtext, required)
   - Featured Image (image)
   - Category (select with options)
   - Published (boolean)
4. Configure each field's properties
5. Reorder fields as needed
6. Save → Content type ready for use

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please read our contributing guidelines.
