# Developer Guide

This guide provides comprehensive information for developers working with or contributing to Bakalr CMS.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Development Setup](#development-setup)
- [Code Style & Conventions](#code-style--conventions)
- [Database Schema](#database-schema)
- [API Development](#api-development)
- [Testing](#testing)
- [Contributing](#contributing)

## Architecture Overview

Bakalr CMS follows a modern, decoupled architecture:

```text
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                       │
│  - React 19 with TypeScript                                 │
│  - TailwindCSS + shadcn/ui                                  │
│  - Client-side routing                                       │
└─────────────────────────────────────────────────────────────┘
                            │
                    HTTP/HTTPS (REST + GraphQL)
                            │
┌─────────────────────────────────────────────────────────────┐
│                   Backend API (FastAPI)                      │
│  - Python 3.11+                                             │
│  - Async/await support                                       │
│  - JWT authentication                                        │
│  - RBAC authorization                                        │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌──────▼───────┐  ┌───────▼────────┐
│   PostgreSQL   │  │    Redis     │  │  Meilisearch   │
│   (Primary)    │  │   (Cache)    │  │    (Search)    │
└────────────────┘  └──────────────┘  └────────────────┘
```

### Technology Stack

#### Backend

- **FastAPI 0.115+**: Modern Python web framework
- **SQLAlchemy 2.0**: ORM with async support
- **Alembic**: Database migrations
- **Pydantic 2.9**: Data validation
- **Python-JOSE**: JWT handling
- **Passlib**: Password hashing (bcrypt)
- **Redis**: Caching and sessions
- **Meilisearch**: Full-text search (optional)
- **Celery**: Background tasks (optional)

#### Frontend

- **Next.js 16**: React framework with SSR/SSG
- **TypeScript 5.6**: Type-safe JavaScript
- **TailwindCSS 3**: Utility-first CSS
- **shadcn/ui**: Component library
- **Axios**: HTTP client
- **React Hook Form**: Form management
- **Zod**: Schema validation

#### Infrastructure

- **Docker**: Containerization
- **Docker Compose**: Multi-container orchestration
- **GitHub Actions**: CI/CD pipelines
- **Nginx**: Reverse proxy (production)

### Key Design Principles

1. **Separation of Concerns**: Clear boundaries between layers
2. **API-First**: Backend is headless, frontend is replaceable
3. **Multi-tenancy**: Organization-level isolation
4. **Security by Default**: JWT, RBAC, CSRF, rate limiting
5. **Performance**: Caching, connection pooling, query optimization
6. **Extensibility**: Plugin-ready architecture

## Project Structure

```text
bakalr-cms/
├── backend/                    # Python/FastAPI backend
│   ├── api/                   # REST API endpoints
│   │   ├── __init__.py
│   │   ├── router.py          # Main API router
│   │   ├── auth.py            # Authentication endpoints
│   │   ├── users.py           # User management
│   │   ├── content.py         # Content management
│   │   ├── translation.py     # Translation endpoints
│   │   ├── media.py           # Media upload/management
│   │   └── ...                # Other endpoints
│   ├── core/                  # Core utilities
│   │   ├── config.py          # Configuration (env vars)
│   │   ├── security.py        # Security utilities
│   │   ├── cache.py           # Redis caching
│   │   ├── permissions.py     # RBAC logic
│   │   ├── rate_limit.py      # Rate limiting
│   │   ├── performance.py     # Performance monitoring
│   │   └── exceptions.py      # Custom exceptions
│   ├── db/                    # Database
│   │   ├── session.py         # DB session management
│   │   └── base.py            # Base model
│   ├── graphql/               # GraphQL API
│   │   ├── schema.py          # GraphQL schema
│   │   ├── types.py           # GraphQL types
│   │   └── context.py         # GraphQL context
│   ├── middleware/            # Middleware
│   │   ├── security.py        # Security middleware
│   │   └── performance.py     # Performance tracking
│   ├── models/                # SQLAlchemy models
│   │   ├── user.py            # User model
│   │   ├── organization.py    # Organization model
│   │   ├── rbac.py            # Role/Permission models
│   │   ├── content.py         # Content models
│   │   └── ...                # Other models
│   ├── templates/             # Email templates
│   │   ├── base.html          # Base template
│   │   ├── password_reset.html
│   │   └── ...
│   ├── main.py                # FastAPI app entry point
│   ├── Dockerfile             # Production Docker image
│   └── Dockerfile.dev         # Development Docker image
├── frontend/                   # Next.js frontend
│   ├── app/                   # App directory (Next.js 13+)
│   │   ├── layout.tsx         # Root layout
│   │   ├── page.tsx           # Home page
│   │   ├── (auth)/            # Auth routes
│   │   └── (dashboard)/       # Dashboard routes
│   ├── components/            # React components
│   │   ├── ui/                # shadcn/ui components
│   │   ├── layout/            # Layout components
│   │   └── ...                # Feature components
│   ├── lib/                   # Utilities
│   │   ├── api.ts             # API client
│   │   ├── auth.ts            # Auth helpers
│   │   └── performance.ts     # Performance monitoring
│   ├── types/                 # TypeScript types
│   │   └── api.ts             # API types
│   ├── public/                # Static assets
│   ├── next.config.ts         # Next.js config
│   ├── tailwind.config.ts     # Tailwind config
│   └── tsconfig.json          # TypeScript config
├── alembic/                    # Database migrations
│   ├── versions/              # Migration scripts
│   └── env.py                 # Alembic config
├── scripts/                    # Utility scripts
│   ├── backup_database.py     # Database backup
│   ├── load_test.py           # Load testing
│   └── ...                    # Other scripts
├── tests/                      # Test files
│   ├── test_auth.py
│   ├── test_content.py
│   └── ...
├── docs/                       # Documentation
│   ├── getting-started.md
│   ├── api.md
│   ├── deployment.md
│   └── ...
├── docker-compose.yml          # Production compose
├── docker-compose.dev.yml      # Development compose
├── .env.example                # Environment template
├── pyproject.toml              # Python dependencies
├── package.json                # Node dependencies
└── README.md                   # Project readme
```

### Backend Structure Explained

#### `/backend/api/`

REST API endpoints organized by resource:
- Each file exports a `router` (APIRouter instance)
- Endpoints follow RESTful conventions
- Use dependency injection for auth/db
- OpenAPI documentation auto-generated

#### `/backend/core/`

Shared utilities and services:
- `config.py`: Settings from environment variables
- `security.py`: JWT, password hashing, CSRF
- `cache.py`: Redis caching wrapper
- `permissions.py`: RBAC logic
- `exceptions.py`: Custom exception classes

#### `/backend/models/`

SQLAlchemy ORM models:
- Each model represents a database table
- Relationships defined with `relationship()`
- Mixins for common fields (timestamps, etc.)
- Type hints for better IDE support

#### `/backend/middleware/`

Custom middleware:
- `SecurityMiddleware`: CSRF, headers, validation
- `PerformanceMiddleware`: Request timing
- Applied in `main.py` order matters!

### Frontend Structure Explained

#### `/frontend/app/`

Next.js App Router (v13+):
- File-based routing
- Route groups with `(name)/`
- Layouts cascade from root
- Server and client components

#### `/frontend/components/`

React components:
- `/ui/`: shadcn/ui primitives
- `/layout/`: Headers, sidebars, etc.
- Feature-specific components
- Reusable, composable

#### `/frontend/lib/`

Utility libraries:
- `api.ts`: Axios instance with interceptors
- `auth.ts`: Token management
- `utils.ts`: Helper functions
- `performance.ts`: Web Vitals tracking

## Development Setup

### Prerequisites

```bash
# Check versions
python --version  # 3.11+
node --version    # 18+
poetry --version  # 1.8+
docker --version  # 24+
```

### Backend Development

```bash
# 1. Clone and enter directory
git clone https://github.com/yourusername/bakalr-cms.git
cd bakalr-cms

# 2. Install Python dependencies
poetry install

# 3. Set up environment
cp .env.example .env
# Edit .env with your settings

# 4. Start services (PostgreSQL, Redis)
docker-compose up -d postgres redis

# 5. Run migrations
poetry run alembic upgrade head

# 6. Create test data (optional)
poetry run python scripts/seed_database.py

# 7. Start development server
poetry run uvicorn backend.main:app --reload
```

Server runs at `http://localhost:8000`

**Hot reload**: Code changes automatically restart the server

### Frontend Development

```bash
# 1. Install dependencies
cd frontend
npm install

# 2. Set up environment
cp .env.local.example .env.local
# Edit NEXT_PUBLIC_API_URL if needed

# 3. Start development server
npm run dev
```

Server runs at `http://localhost:3000`

**Hot reload**: Code changes automatically update the page

### Database Migrations

```bash
# Create new migration
poetry run alembic revision --autogenerate -m "Add user preferences"

# Apply migrations
poetry run alembic upgrade head

# Rollback one migration
poetry run alembic downgrade -1

# Show current version
poetry run alembic current

# Show history
poetry run alembic history
```

### Running Tests

```bash
# Backend tests
poetry run pytest

# With coverage
poetry run pytest --cov=backend --cov-report=html

# Specific test file
poetry run pytest tests/test_auth.py

# Frontend tests
cd frontend
npm run test

# E2E tests
npm run test:e2e
```

## Code Style & Conventions

### Python (Backend)

Follow [PEP 8](https://pep8.org/) with these additions:

```python
# Use type hints
def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

# Async functions where appropriate
async def send_email(to: str, subject: str, body: str) -> bool:
    # Implementation
    pass

# Docstrings for public functions
def calculate_total(items: List[Item]) -> Decimal:
    """
    Calculate total price for list of items.

    Args:
        items: List of Item objects

    Returns:
        Total price as Decimal
    """
    return sum(item.price for item in items)

# Use dependency injection
@router.get("/users/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(SessionLocal)
):
    return current_user
```

**Naming Conventions:**
- Functions/methods: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_CASE`
- Private: `_leading_underscore`

### TypeScript (Frontend)

Follow [Airbnb Style Guide](https://github.com/airbnb/javascript):

```typescript
// Use interfaces for object shapes
interface User {
  id: number;
  email: string;
  fullName: string;
}

// Use type for unions/intersections
type Status = 'pending' | 'approved' | 'rejected';

// Arrow functions for components
export const UserCard: React.FC<{ user: User }> = ({ user }) => {
  return (
    <div className="user-card">
      <h3>{user.fullName}</h3>
      <p>{user.email}</p>
    </div>
  );
};

// Async/await for API calls
async function fetchUser(id: number): Promise<User> {
  const response = await api.get(`/users/${id}`);
  return response.data;
}
```

**Naming Conventions:**
- Components: `PascalCase`
- Functions/variables: `camelCase`
- Constants: `UPPER_CASE`
- Files: Match component name or `kebab-case`

### Git Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```text
feat: add user profile page
fix: resolve login redirect issue
docs: update API documentation
style: format code with prettier
refactor: simplify auth middleware
test: add tests for content API
chore: update dependencies
```

## Database Schema

### Core Tables

**users**: User accounts
```sql
id, email, password_hash, full_name, organization_id,
is_active, is_superuser, created_at, updated_at
```

**organizations**: Multi-tenant organizations
```sql
id, name, slug, settings, created_at, updated_at
```

**roles**: RBAC roles
```sql
id, name, description, organization_id, created_at
```

**permissions**: RBAC permissions
```sql
id, name, description, resource, action,
content_type_id, field_name
```

**content_types**: Content schemas
```sql
id, name, slug, schema, organization_id, created_at
```

**content_entries**: Content instances
```sql
id, content_type_id, title, slug, fields, status,
version, published_at, created_at, updated_at
```

### Relationships

```text
organizations 1──────* users
organizations 1──────* roles
roles *──────* permissions
users *──────* roles
organizations 1──────* content_types
content_types 1──────* content_entries
content_entries *──────* translations
content_entries *──────* media
```

See `docs/database-schema.md` for complete schema documentation.

## API Development

### Creating New Endpoints

1. **Define the model** (`backend/models/`)
```python
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"))
```

2. **Create Pydantic schemas** (in endpoint file)
```python
class ProductCreate(BaseModel):
    name: str
    price: Decimal

class ProductResponse(BaseModel):
    id: int
    name: str
    price: Decimal

    class Config:
        from_attributes = True
```

3. **Implement endpoints** (`backend/api/`)
```python
router = APIRouter(prefix="/products", tags=["products"])

@router.post("/", response_model=ProductResponse)
def create_product(
    product: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(SessionLocal)
):
    db_product = Product(**product.dict(), organization_id=current_user.organization_id)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.get("/", response_model=List[ProductResponse])
def list_products(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(SessionLocal)
):
    products = db.query(Product).filter(
        Product.organization_id == current_user.organization_id
    ).offset(skip).limit(limit).all()
    return products
```

4. **Register router** (`backend/api/router.py`)
```python
from backend.api import products

api_router.include_router(products.router)
```

5. **Add tests** (`tests/test_products.py`)
```python
def test_create_product(client, auth_headers):
    response = client.post(
        "/api/v1/products",
        json={"name": "Widget", "price": 9.99},
        headers=auth_headers
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Widget"
```

### Authentication & Authorization

**Require authentication:**
```python
current_user: User = Depends(get_current_user)
```

**Require specific permission:**
```python
PermissionChecker.require_permission(current_user, "products.create", db)
```

**Check permission:**
```python
if not PermissionChecker.has_permission(current_user, "products.delete", db):
    raise HTTPException(status_code=403, detail="Permission denied")
```

## Testing

### Backend Tests

```python
# tests/test_products.py
import pytest
from fastapi.testclient import TestClient

def test_create_product(client: TestClient, auth_headers: dict):
    """Test product creation"""
    response = client.post(
        "/api/v1/products",
        json={"name": "Widget", "price": 9.99},
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Widget"
    assert float(data["price"]) == 9.99

def test_list_products(client: TestClient, auth_headers: dict, sample_products):
    """Test listing products"""
    response = client.get("/api/v1/products", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == len(sample_products)
```

### Frontend Tests

```typescript
// components/__tests__/UserCard.test.tsx
import { render, screen } from '@testing-library/react';
import { UserCard } from '../UserCard';

describe('UserCard', () => {
  it('renders user information', () => {
    const user = {
      id: 1,
      email: 'test@example.com',
      fullName: 'Test User'
    };

    render(<UserCard user={user} />);

    expect(screen.getByText('Test User')).toBeInTheDocument();
    expect(screen.getByText('test@example.com')).toBeInTheDocument();
  });
});
```

### Test Coverage

Run coverage reports:

```bash
# Backend
poetry run pytest --cov=backend --cov-report=html
open htmlcov/index.html

# Frontend
npm run test:coverage
```

## Contributing

We welcome contributions! See [CONTRIBUTING.md](../CONTRIBUTING.md) for:

- Code of Conduct
- Development workflow
- Pull request process
- Coding standards
- Documentation requirements

### Quick Contribution Guide

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Make your changes**
4. **Add tests**
5. **Run tests and linters**
   ```bash
   poetry run pytest
   poetry run black backend
   poetry run flake8 backend
   ```
6. **Commit with conventional message**
   ```bash
   git commit -m "feat: add amazing feature"
   ```
7. **Push and create pull request**

## Resources

- **FastAPI Docs**: <https://fastapi.tiangolo.com/>
- **SQLAlchemy Docs**: <https://docs.sqlalchemy.org/>
- **Next.js Docs**: <https://nextjs.org/docs>
- **TailwindCSS Docs**: <https://tailwindcss.com/docs>
- **Python Type Hints**: <https://docs.python.org/3/library/typing.html>
- **TypeScript Handbook**: <https://www.typescriptlang.org/docs/>

## Need Help?

- **Documentation**: Check `/docs` directory
- **API Reference**: <http://localhost:8000/api/docs>
- **GitHub Issues**: Report bugs or request features
- **Discussions**: Community Q&A
- **Discord**: Join our community server

Happy coding! 🚀
