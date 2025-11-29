# Getting Started with Bakalr CMS

Welcome to Bakalr CMS! This guide will help you get up and running quickly.

## Table of Contents

- [What is Bakalr CMS?](#what-is-bakalr-cms)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [First Steps](#first-steps)
- [Core Concepts](#core-concepts)
- [Next Steps](#next-steps)

## What is Bakalr CMS?

Bakalr CMS is a modern, production-ready headless Content Management System built with:

- **Backend**: FastAPI (Python) with PostgreSQL/SQLite
- **Frontend**: Next.js 16 with TypeScript and TailwindCSS
- **Features**: Multi-tenancy, RBAC, auto-translation, search, webhooks, and more

### Key Features

✨ **Content Management**: Dynamic content types with versioning and relationships
🔐 **Security**: JWT authentication, 2FA, API keys, RBAC with field-level permissions
🌍 **Multi-language**: Automatic translation to 100+ languages
🔍 **Search**: Meilisearch-powered full-text search with typo tolerance
📊 **Analytics**: Content usage, user activity, search analytics
🎨 **Theming**: Custom themes with Dark Chocolate Brown default
🔔 **Notifications**: In-app notifications with email delivery
🪝 **Webhooks**: Event-driven webhooks with HMAC signatures
⚡ **Performance**: Query optimization, caching, connection pooling
🐳 **DevOps**: Docker-ready with CI/CD pipelines

## Quick Start

The fastest way to get started:

```bash
# Clone the repository
git clone https://github.com/yourusername/bakalr-cms.git
cd bakalr-cms

# Start with Docker Compose
docker-compose up -d

# Access the application
# Backend API: http://localhost:8000
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/api/docs
```

That's it! The default admin credentials are in the `.env.example` file.

## Installation

### Prerequisites

- **Python 3.11+** (for backend)
- **Node.js 18+** (for frontend)
- **PostgreSQL 14+** or SQLite (database)
- **Redis 7+** (caching)
- **Meilisearch v1.5+** (optional, for search)

### Option 1: Docker (Recommended)

```bash
# 1. Clone repository
git clone https://github.com/yourusername/bakalr-cms.git
cd bakalr-cms

# 2. Configure environment
cp .env.example .env
# Edit .env with your settings

# 3. Start services
docker-compose up -d

# 4. Run migrations
docker-compose exec backend alembic upgrade head

# 5. Create admin user (optional)
docker-compose exec backend python scripts/create_admin.py
```

### Option 2: Local Development

#### Backend Setup

```bash
# 1. Install Poetry (Python package manager)
curl -sSL https://install.python-poetry.org | python3 -

# 2. Install dependencies
cd backend
poetry install

# 3. Configure environment
cp .env.example .env
# Edit .env with your database credentials

# 4. Run migrations
poetry run alembic upgrade head

# 5. Start backend server
poetry run uvicorn backend.main:app --reload
```

Backend will be available at `http://localhost:8000`

#### Frontend Setup

```bash
# 1. Install dependencies
cd frontend
npm install

# 2. Configure environment
cp .env.local.example .env.local
# Edit .env.local with your API URL

# 3. Start development server
npm run dev
```

Frontend will be available at `http://localhost:3000`

#### Additional Services

**PostgreSQL** (recommended for production):
```bash
# macOS
brew install postgresql@16
brew services start postgresql@16

# Ubuntu/Debian
sudo apt install postgresql-16
sudo systemctl start postgresql
```

**Redis** (required for caching):
```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis
```

**Meilisearch** (optional, for search):
```bash
# macOS
brew install meilisearch
brew services start meilisearch

# Ubuntu/Debian
curl -L https://install.meilisearch.com | sh
./meilisearch
```

## First Steps

### 1. Register an Account

Navigate to `http://localhost:3000/register` or use the API:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "SecurePassword123!",
    "full_name": "Admin User",
    "organization_name": "My Company"
  }'
```

This creates both a user and an organization.

### 2. Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "SecurePassword123!"
  }'
```

Save the `access_token` from the response.

### 3. Create Your First Content Type

Content types define the structure of your content:

```bash
curl -X POST http://localhost:8000/api/v1/content-types \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Blog Post",
    "slug": "blog-post",
    "schema": {
      "title": {"type": "string", "required": true},
      "body": {"type": "text", "required": true},
      "author": {"type": "string"},
      "published_date": {"type": "date"}
    }
  }'
```

### 4. Create Content

```bash
curl -X POST http://localhost:8000/api/v1/content/entries \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content_type_id": 1,
    "title": "My First Blog Post",
    "slug": "my-first-post",
    "status": "published",
    "fields": {
      "title": "Welcome to Bakalr CMS",
      "body": "This is my first blog post!",
      "author": "Admin User",
      "published_date": "2025-11-25"
    }
  }'
```

### 5. Retrieve Content

```bash
# List all content
curl http://localhost:8000/api/v1/content/entries \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get specific content
curl http://localhost:8000/api/v1/content/entries/1 \
  -H "Authorization: Bearer YOUR_TOKEN"

# Search content
curl "http://localhost:8000/api/v1/search?q=welcome" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Core Concepts

### Organizations (Multi-tenancy)

Every user belongs to at least one organization. Content, users, and settings are isolated by organization.

```bash
# Create organization
POST /api/v1/organizations

# Switch organization
POST /api/v1/tenant/switch
```

### Roles & Permissions

Fine-grained access control with role-based permissions:

- **super_admin**: Full system access
- **admin**: Organization administration
- **editor**: Content creation and editing
- **viewer**: Read-only access

```bash
# Create custom role
POST /api/v1/roles

# Assign permissions
POST /api/v1/roles/{role_id}/permissions
```

### Content Types

Define the structure of your content with JSON schemas:

```json
{
  "name": "Product",
  "slug": "product",
  "schema": {
    "name": {"type": "string", "required": true},
    "price": {"type": "number", "required": true},
    "description": {"type": "text"},
    "images": {"type": "array", "items": {"type": "string"}},
    "category": {"type": "reference", "to": "category"}
  }
}
```

### Content Entries

Actual content instances based on content types:

```json
{
  "content_type_id": 1,
  "title": "Awesome Product",
  "slug": "awesome-product",
  "status": "published",
  "fields": {
    "name": "Awesome Product",
    "price": 99.99,
    "description": "The best product ever",
    "images": ["image1.jpg", "image2.jpg"]
  }
}
```

### Translations

Automatic translation to enabled locales:

```bash
# Enable locale
POST /api/v1/translation/locales
{"code": "es", "name": "Spanish", "enabled": true}

# Content is automatically translated
# Access translated content
GET /api/v1/content/entries/1?locale=es
```

### Media Management

Upload and manage files:

```bash
# Upload file
curl -X POST http://localhost:8000/api/v1/media/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@image.jpg" \
  -F "alt_text=Product Image"

# List media
GET /api/v1/media
```

### Webhooks

Subscribe to events:

```bash
# Create webhook
POST /api/v1/webhooks
{
  "url": "https://example.com/webhook",
  "events": ["content.created", "content.published"],
  "secret": "your-secret-key"
}
```

Events are sent with HMAC-SHA256 signatures for verification.

## Next Steps

Now that you're set up, explore these areas:

### 📚 Documentation

- [API Reference](http://localhost:8000/api/docs) - Interactive API documentation
- [Authentication Guide](./authentication.md) - JWT, 2FA, API keys
- [Security Guide](./security.md) - Best practices and hardening
- [Performance Guide](./performance.md) - Optimization and monitoring
- [Deployment Guide](./deployment.md) - Docker and production setup

### 🎓 Tutorials

1. **[Create a Blog](./tutorials/blog.md)** - Build a simple blog
2. **[E-commerce Site](./tutorials/ecommerce.md)** - Product catalog with search
3. **[Multi-language Site](./tutorials/multilang.md)** - International content
4. **[Custom Workflows](./tutorials/workflows.md)** - Approval processes

### 🔧 Advanced Features

- **GraphQL API**: Alternative to REST at `/api/v1/graphql`
- **Content Relationships**: Link content entries together
- **Content Templates**: Reusable content blueprints
- **Scheduled Publishing**: Publish content at specific times
- **Field-level Permissions**: Granular access control
- **Analytics Dashboard**: Track content performance
- **Custom Themes**: Brand your CMS

### 💡 Examples

Check out example implementations:

- **Blog**: `examples/blog/`
- **E-commerce**: `examples/ecommerce/`
- **Documentation Site**: `examples/docs/`
- **Portfolio**: `examples/portfolio/`

### 🆘 Getting Help

- **Documentation**: Full docs at `/docs`
- **API Reference**: Interactive docs at `/api/docs`
- **GitHub Issues**: Report bugs or request features
- **Discussions**: Community Q&A on GitHub
- **Discord**: Join our community server

### 🚀 Production Deployment

When you're ready for production:

1. **Review [Security Guide](./security.md)** - Harden your installation
2. **Configure [Environment Variables](./deployment.md#environment)** - Production settings
3. **Set up [Database Backups](./deployment.md#backups)** - Protect your data
4. **Enable [Performance Monitoring](./performance.md)** - Track metrics
5. **Configure [CI/CD](./deployment.md#cicd)** - Automated deployments

## Common Tasks

### Reset Password

```bash
POST /api/v1/auth/password-reset/request
{"email": "user@example.com"}

# Check email for reset token
POST /api/v1/auth/password-reset/confirm
{"token": "...", "new_password": "NewPassword123!"}
```

### Enable 2FA

```bash
# Generate secret
POST /api/v1/auth/2fa/setup

# Verify with authenticator app
POST /api/v1/auth/2fa/enable
{"token": "123456"}
```

### Create API Key

```bash
POST /api/v1/api-keys
{
  "name": "Mobile App Key",
  "permissions": ["content.read", "media.read"],
  "expires_at": "2026-12-31T23:59:59Z"
}
```

### Backup Database

```bash
# Using the backup script
python scripts/backup_database.py

# Manual PostgreSQL backup
pg_dump -U postgres bakalr_cms > backup.sql

# SQLite backup
sqlite3 bakalr_cms.db ".backup backup.db"
```

## Troubleshooting

### Backend won't start

**Check logs**:
```bash
docker-compose logs backend
# or
tail -f backend/logs/app.log
```

**Common issues**:
- Database connection failed → Check `DATABASE_URL` in `.env`
- Redis connection failed → Ensure Redis is running
- Port already in use → Change `BACKEND_PORT` in `.env`

### Frontend won't start

**Clear cache**:
```bash
cd frontend
rm -rf .next node_modules
npm install
npm run dev
```

**Common issues**:
- API connection failed → Check `NEXT_PUBLIC_API_URL` in `.env.local`
- Build errors → Run `npm run build` to see detailed errors
- Port already in use → Change port with `npm run dev -- -p 3001`

### Database migrations fail

```bash
# Reset database (WARNING: deletes all data)
poetry run alembic downgrade base
poetry run alembic upgrade head

# Or with Docker
docker-compose exec backend alembic downgrade base
docker-compose exec backend alembic upgrade head
```

### Search not working

```bash
# Check Meilisearch status
curl http://localhost:7700/health

# Reindex content
POST /api/v1/search/reindex
```

## FAQ

**Q: Can I use this in production?**
A: Yes! Bakalr CMS is production-ready with security hardening, performance optimization, and comprehensive testing.

**Q: Do I need Meilisearch?**
A: No, it's optional. Basic search works without it, but Meilisearch provides advanced features like typo tolerance and faceted search.

**Q: Can I customize the frontend?**
A: Absolutely! The frontend is built with Next.js and TailwindCSS, making it easy to customize.

**Q: How do I migrate from another CMS?**
A: Check the [migration guide](./migration.md) for importing data from WordPress, Contentful, Strapi, etc.

**Q: Is there a hosted version?**
A: Currently Bakalr CMS is self-hosted. A managed cloud version is planned for the future.

**Q: What's the license?**
A: Bakalr Proprietary License - all rights reserved. For licensing inquiries, contact <info@bakalr.com>.

## What's Next?

Ready to dive deeper? Check out:

- **[API Documentation](http://localhost:8000/api/docs)** - Full API reference
- **[Search & Discovery Guide](./search.md)** - Full-text search with Meilisearch
- **[Webhooks Guide](./webhooks.md)** - Event-driven integrations
- **[Developer Guide](./developer-guide.md)** - Architecture and code structure
- **[Deployment Guide](./deployment.md)** - Production deployment
- **[Contributing Guide](../CONTRIBUTING.md)** - Help improve Bakalr CMS

Happy building! 🚀
