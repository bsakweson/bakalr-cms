# Changelog

All notable changes to Bakalr CMS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-11-25

### 🎉 Initial Release

Bakalr CMS v0.1.0 marks the first production-ready release of our modern headless CMS platform.

### ✨ Features

#### Core Platform

- **Multi-tenancy**: Full organization/workspace isolation with tenant switching
- **Authentication**: JWT-based auth with refresh tokens, 2FA (TOTP), password reset flow
- **Authorization**: Comprehensive RBAC with field-level permissions and permission hierarchies
- **API**: 159+ REST endpoints across 24 modules + GraphQL API with 8 queries and 2 mutations

#### Content Management

- **Dynamic Content Types**: JSON schema-based content modeling with validation
- **Content Entries**: Full CRUD operations with versioning and status management
- **Content Relationships**: Bidirectional linking (one-to-many, many-to-one, many-to-many)
- **Content Templates**: Reusable blueprints with field defaults and configurations
- **Scheduled Publishing**: Automatic status updates with timezone support

#### Multi-language & Translation

- **Auto-translation**: Automatic translation to 100+ languages via Google Translate
- **Locale Management**: Enable/disable locales per organization
- **Translation Caching**: Redis-based caching with 24-hour TTL
- **Fallback Support**: Automatic fallback to default locale

#### Media Management

- **File Upload**: Multi-file upload with drag-and-drop support
- **Storage Backends**: S3-compatible storage and local filesystem
- **Image Processing**: Automatic thumbnail generation with Pillow
- **CDN Support**: CDN-ready URLs with cache headers
- **Media Library**: Browse, search, and filter uploaded media

#### Search & Discovery

- **Full-text Search**: Meilisearch integration with fuzzy matching and typo tolerance
- **Advanced Filtering**: Faceted search with multiple filters
- **Search Analytics**: Track search queries and results
- **Autocomplete**: Real-time search suggestions
- **Highlighting**: Search term highlighting in results

#### SEO Management

- **Meta Tags**: Title, description, keywords, Open Graph, Twitter Cards
- **Sitemaps**: Automatic XML sitemap generation with priority and frequency
- **Structured Data**: Schema.org JSON-LD markup
- **Robots.txt**: Dynamic robots.txt generation
- **Canonical URLs**: Prevent duplicate content issues

#### Webhooks & Events

- **Event System**: 6 event types (created, updated, deleted, published, scheduled, unpublished)
- **HMAC Signatures**: Secure webhook payloads with HMAC-SHA256
- **Retry Logic**: Exponential backoff with configurable max attempts
- **Webhook Logs**: Track delivery status and response codes

#### Notifications & Email

- **In-app Notifications**: Real-time notifications with read/unread status
- **Email Service**: Template-based email delivery with HTML/text fallback
- **Email Templates**: Customizable Jinja2 templates
- **Notification Preferences**: Per-user notification settings
- **Batch Operations**: Mark all as read, delete notifications

#### User Management

- **User CRUD**: Create, read, update, delete users
- **Profile Management**: Update profile, change password
- **Multi-organization**: Users can belong to multiple organizations
- **Role Assignment**: Assign roles per organization
- **API Key Management**: Generate API keys with expiration and permissions

#### Security Features

- **JWT Authentication**: Access and refresh tokens with configurable expiration
- **Two-Factor Auth**: TOTP-based 2FA with backup codes
- **Password Security**: Bcrypt hashing with minimum strength requirements
- **CSRF Protection**: Double-submit cookie pattern
- **Rate Limiting**: Per-user, per-tenant, and per-IP limits
- **Security Headers**: CSP, HSTS, X-Frame-Options, X-Content-Type-Options
- **CORS Configuration**: Configurable allowed origins

#### Performance Optimizations

- **Query Optimization**: N+1 prevention, eager loading, batch operations
- **Connection Pooling**: Environment-based pool sizing with automatic recycling
- **Redis Caching**: Response caching with ETag support and cache warming
- **Performance Monitoring**: Request timing, endpoint stats, system metrics
- **Metrics API**: 7 admin endpoints for performance data
- **Web Vitals**: LCP, FID, CLS tracking on frontend

#### Analytics & Insights

- **Content Analytics**: View counts, update frequency, popularity metrics
- **User Activity**: Track user actions and login history
- **Search Analytics**: Popular queries, zero-result searches, CTR
- **System Metrics**: CPU, memory, disk usage, connection pool stats
- **Custom Reports**: Generate reports for date ranges

#### Theming

- **Custom Themes**: Define color palettes, typography, spacing, shadows
- **Dark Chocolate Default**: Professional dark theme with chocolate brown accent
- **Theme API**: 11 endpoints for theme management
- **Per-organization**: Each organization can have custom themes

#### Frontend (Next.js)

- **Modern UI**: Next.js 16 with TypeScript and TailwindCSS
- **Component Library**: shadcn/ui components with accessibility
- **Responsive Design**: Mobile-first responsive layouts
- **Authentication Flow**: Login, register, password reset, 2FA setup
- **Admin Dashboard**: Content management interface
- **Performance**: Code splitting, lazy loading, image optimization

#### API Features

- **REST API**: 159+ endpoints with OpenAPI documentation
- **GraphQL API**: Flexible querying with GraphiQL playground
- **API Versioning**: URL-based versioning with deprecation headers
- **Pagination**: Cursor and offset pagination support
- **Filtering**: Advanced filtering on all list endpoints
- **Sorting**: Multi-field sorting support
- **Error Handling**: RFC 7807 Problem Details format

#### DevOps & Deployment

- **Docker**: Multi-stage builds for backend and frontend
- **Docker Compose**: Full stack orchestration for development and production
- **CI/CD**: GitHub Actions workflows for testing, building, and security scanning
- **Health Checks**: Liveness and readiness probes
- **Migrations**: Alembic database migrations
- **Environment Config**: 12-factor app with environment variables

#### Documentation

- **Getting Started**: Comprehensive installation and first steps guide
- **Developer Guide**: Architecture, project structure, development setup
- **API Documentation**: Interactive OpenAPI/Swagger docs
- **Performance Guide**: Optimization techniques and monitoring
- **Security Guide**: Best practices and hardening
- **Deployment Guide**: Docker and production deployment
- **Authentication Guide**: JWT, 2FA, API keys

### 🔧 Technical Details

#### Backend Stack

- FastAPI 0.115+ (Python web framework)
- SQLAlchemy 2.0 (ORM with async support)
- Alembic 1.13+ (database migrations)
- Pydantic 2.9+ (data validation)
- Redis 5.0+ (caching and sessions)
- PostgreSQL 14+ or SQLite (database)
- Meilisearch v1.5+ (search engine, optional)
- Python 3.11+ required

#### Frontend Stack

- Next.js 16.0.4 (React framework)
- React 19 (UI library)
- TypeScript 5.6+ (type safety)
- TailwindCSS 3 (styling)
- shadcn/ui (component library)
- Axios (HTTP client)
- Node.js 18+ required

#### Database Schema

- 27 tables total
- Full relational integrity
- Optimized indexes
- JSON fields for flexible schemas
- Timestamp tracking on all entities

#### API Modules (24)

1. Analytics (11 endpoints)
2. Auth (7 endpoints)
3. Users (6 endpoints)
4. Roles (8 endpoints)
5. Organizations (6 endpoints)
6. Audit Logs (3 endpoints)
7. Two-Factor Auth (8 endpoints)
8. Password Reset (3 endpoints)
9. API Keys (5 endpoints)
10. Tenant Switching (5 endpoints)
11. Content Types (5 endpoints)
12. Content Entries (11 endpoints)
13. Content Relationships (5 endpoints)
14. Translations (11 endpoints)
15. SEO (10 endpoints)
16. Media (11 endpoints)
17. Webhooks (10 endpoints)
18. Preview (5 endpoints)
19. Delivery (4 endpoints)
20. Scheduled Publishing (9 endpoints)
21. Field Permissions (8 endpoints)
22. Themes (11 endpoints)
23. Content Templates (9 endpoints)
24. Notifications (13 endpoints)
25. Search (8 endpoints)
26. Metrics (7 endpoints)

### 📊 Statistics

- **159+ REST Endpoints**: Comprehensive API coverage
- **27 Database Tables**: Well-structured schema
- **51+ Test Suites**: Thorough test coverage
- **8 GraphQL Queries**: Flexible data fetching
- **100+ Languages**: Auto-translation support
- **6 Event Types**: Webhook event system
- **2000+ Lines**: Documentation across 10 guides

### 🔒 Security

- JWT token authentication with refresh tokens
- TOTP-based two-factor authentication
- Bcrypt password hashing (cost factor 12)
- CSRF protection with double-submit cookies
- Rate limiting (100 req/min authenticated, 20 req/min anonymous)
- Security headers (CSP, HSTS, X-Frame-Options)
- CORS with configurable origins
- API key authentication with expiration
- Field-level permission masking
- HMAC-SHA256 webhook signatures
- SQL injection prevention (parameterized queries)
- XSS protection (input sanitization)

### ⚡ Performance

- Redis caching with ETag support
- Connection pooling (prod: 20/40, staging: 10/20, dev: 5/10)
- Query optimization with N+1 prevention
- Bulk operations for large datasets
- CDN-ready with cache headers
- Image optimization (WebP/AVIF)
- Code splitting and lazy loading
- Performance monitoring with p95/p99 metrics
- Slow query tracking (>100ms)
- System metrics (CPU, memory, disk)

### 📦 Dependencies

#### Backend (Major)

- fastapi==0.115.0
- uvicorn==0.32.0
- sqlalchemy==2.0.0
- alembic==1.13.0
- pydantic==2.9.0
- python-jose==3.5.0
- passlib==1.7.4
- redis==5.0.0
- psycopg2-binary==2.9.9
- pillow==12.0.0
- boto3==1.41.3
- psutil==7.1.3

#### Frontend (Major)

- next==16.0.4
- react==19.0.0
- typescript==5.6.3
- tailwindcss==3.4.1
- axios==1.7.9

### 🐳 Docker

- Multi-stage builds for optimized images
- Backend image: ~200MB (Python 3.11-slim)
- Frontend image: ~150MB (Node 18-alpine)
- Docker Compose for full stack
- Health checks for all services
- Development and production configurations

### 🚀 Deployment

- Docker deployment ready
- Kubernetes manifests included
- Environment-based configuration
- Database migration automation
- CI/CD pipelines (GitHub Actions)
- Health check endpoints
- Graceful shutdown support
- Zero-downtime deployments

### 📝 Known Limitations

- Meilisearch is optional but recommended for production search
- Email sending requires SMTP configuration
- S3 storage requires AWS credentials or compatible service
- Two-factor auth requires time synchronization
- WebSocket support not yet implemented for real-time features

### 🔮 Coming Soon

- Content collaboration (comments, mentions)
- Advanced workflows (approval chains)
- White-label customization
- Enhanced analytics dashboard
- Mobile apps (iOS/Android)
- Plugin system
- Marketplace for extensions

### 🙏 Acknowledgments

Built with these amazing open-source projects:
- FastAPI, SQLAlchemy, Pydantic (backend)
- Next.js, React, TailwindCSS (frontend)
- PostgreSQL, Redis, Meilisearch (infrastructure)
- Docker, GitHub Actions (DevOps)

### 📄 License

Bakalr Proprietary License - see [LICENSE](LICENSE) file for details

---

## Future Releases

### [0.2.0] - Planned

- Real-time collaboration features
- Advanced workflow system
- Plugin architecture
- Enhanced mobile experience
- Performance improvements

---

[0.1.0]: https://github.com/yourusername/bakalr-cms/releases/tag/v0.1.0
