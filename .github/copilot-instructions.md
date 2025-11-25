# Bakalr CMS - Copilot Instructions

This workspace contains **Bakalr CMS v0.1.0** - a production-ready headless CMS built with FastAPI (backend) and Next.js (frontend).

## Project Overview

- **Backend**: Python 3.11+ with FastAPI, SQLAlchemy, PostgreSQL
- **Frontend**: Next.js 16, React 19, TypeScript, TailwindCSS
- **Features**: Multi-tenancy, RBAC, auto-translation (100+ languages), full-text search (Meilisearch), SEO, webhooks, 2FA
- **API**: 159+ REST endpoints + GraphQL API
- **Documentation**: 2000+ lines across getting-started, developer-guide, deployment, security, performance guides

## Development Setup

### Quick Start with Docker
```bash
docker-compose up -d
```

### Local Development
Backend:
```bash
poetry install
poetry run alembic upgrade head
poetry run uvicorn backend.main:app --reload
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

### VS Code Tasks
- **Start Backend Server**: Runs FastAPI on port 8000
- **Start Frontend Server**: Runs Next.js on port 3000
- **Start Full Stack**: Runs both servers

## Code Style

- **Backend**: PEP 8, type hints, docstrings
- **Frontend**: Airbnb TypeScript, ESLint, Prettier
- **Git**: Conventional Commits (feat:, fix:, docs:, etc.)

## Key Directories

- `/backend` - FastAPI application (API, models, services)
- `/frontend` - Next.js application (UI components, pages)
- `/docs` - Documentation (getting-started, developer-guide, etc.)
- `/alembic` - Database migrations
- `/.vscode` - VS Code tasks and settings

## Documentation

- [Getting Started Guide](../docs/getting-started.md) - Installation and first steps
- [Developer Guide](../docs/developer-guide.md) - Architecture and contribution
- [README](../README.md) - Project overview
- [CHANGELOG](../CHANGELOG.md) - Version history

## Implementation Status

All 23 phases complete:
✅ Authentication, RBAC, Multi-tenancy, Content Management, Translation, SEO, Media, Webhooks, Search, Analytics, 2FA, Performance, Security, Deployment, Documentation

**Future enhancements** (v0.2.0): WebSocket/real-time features, SSO, advanced search facets, CLI tool, mobile SDK
