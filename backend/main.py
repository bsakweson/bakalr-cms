"""
FastAPI application configuration and initialization
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from strawberry.fastapi import GraphQLRouter
from scalar_fastapi import get_scalar_api_reference

from backend.core.config import settings
from backend.api import api_router
from backend.core.cache import cache
from backend.core.rate_limit import limiter
from backend.core.versioning import VersioningMiddleware
from backend.core.cache_warming import cache_warming_service
from backend.core.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from backend.graphql.schema import schema
from backend.graphql.context import get_graphql_context


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle events for the FastAPI application
    """
    # Startup
    print(f"🚀 Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    print(f"📝 Environment: {settings.ENVIRONMENT}")
    print(f"🔧 Debug mode: {settings.DEBUG}")
    
    # TODO: Enable cache warming in production
    # if not settings.DEBUG:
    #     print("🔥 Warming cache...")
    #     await cache_warming_service.warm_all()
    
    yield
    
    # Shutdown
    print("👋 Shutting down...")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="""
## Bakalr CMS - Headless CMS API

A modern, production-ready headless CMS with comprehensive features for content management, 
multi-tenancy, role-based access control, and more.

### Key Features

- 🔐 **Authentication & Authorization**: JWT tokens, API keys, 2FA, OAuth2
- 👥 **Multi-tenancy**: Organization/workspace isolation with tenant switching
- 🛡️ **RBAC**: Comprehensive role-based access control with field-level permissions
- 📝 **Content Management**: Dynamic content types with versioning and relationships
- 🌍 **Multi-language**: Automatic translation support with Google Translate
- 🔍 **Search**: Meilisearch-powered full-text search with fuzzy matching
- 📊 **SEO**: Meta tags, sitemaps, structured data (schema.org)
- 📁 **Media**: File upload with thumbnails, S3/local storage, CDN support
- 🎨 **Theming**: Custom themes with dark chocolate brown default
- 🔔 **Notifications**: In-app notifications with email delivery
- 🪝 **Webhooks**: Event-driven webhooks with HMAC signatures and retry logic
- 🔄 **Caching**: Redis-based caching with ETags and cache warming
- ⚡ **Rate Limiting**: Per-user, per-tenant, and per-IP limits
- 📈 **GraphQL**: Flexible query interface alongside REST API

### Base URL

- **Production**: `https://api.yourdomain.com`
- **Development**: `http://localhost:8000`

### API Versioning

This API uses URL-based versioning:
- Current version: `/api/v1/`
- All endpoints are prefixed with the version number

### Authentication

Most endpoints require authentication using one of:
1. **JWT Bearer Token**: `Authorization: Bearer <token>`
2. **API Key**: `X-API-Key: <your-api-key>`

Get started by registering an account at `/api/v1/auth/register`.

### Rate Limiting

- **Authenticated users**: 100 requests/minute
- **Unauthenticated**: 20 requests/minute
- Rate limit info is returned in response headers

### Support

- 📖 Documentation: [GitHub](https://github.com/yourusername/bakalr-cms)
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/bakalr-cms/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/yourusername/bakalr-cms/discussions)
        """,
        version=settings.VERSION,
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
        openapi_url="/api/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
        contact={
            "name": "Bakalr CMS Support",
            "url": "https://github.com/yourusername/bakalr-cms",
            "email": "support@yourdomain.com",
        },
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
        openapi_tags=[
            {"name": "auth", "description": "Authentication and authorization operations"},
            {"name": "users", "description": "User management"},
            {"name": "organizations", "description": "Organization/tenant management"},
            {"name": "roles", "description": "Role and permission management"},
            {"name": "content-types", "description": "Content type schema management"},
            {"name": "content", "description": "Content entry operations"},
            {"name": "media", "description": "Media file upload and management"},
            {"name": "translation", "description": "Multi-language translation"},
            {"name": "seo", "description": "SEO metadata and sitemap generation"},
            {"name": "webhooks", "description": "Webhook configuration and logs"},
            {"name": "search", "description": "Full-text search with Meilisearch"},
            {"name": "notifications", "description": "In-app notifications"},
            {"name": "themes", "description": "Custom theming"},
            {"name": "audit", "description": "Audit log viewer"},
        ],
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_cors_origins_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # API versioning middleware
    app.add_middleware(VersioningMiddleware)

    # Rate limiting state
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Custom rate limit exceeded handler
    @app.exception_handler(RateLimitExceeded)
    async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limit_exceeded",
                "message": "Too many requests. Please try again later.",
                "detail": str(exc.detail) if hasattr(exc, 'detail') else None
            },
            headers={
                "Retry-After": str(exc.detail) if hasattr(exc, 'detail') else "60"
            }
        )

    # Register exception handlers (RFC 7807 Problem Details)
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Include API router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    
    # Include GraphQL router
    graphql_app = GraphQLRouter(
        schema,
        context_getter=get_graphql_context,
        graphiql=settings.DEBUG,  # Enable GraphiQL playground in debug mode
    )
    app.include_router(graphql_app, prefix="/api/v1/graphql")
    
    # Scalar API documentation (modern interactive UI)
    @app.get("/api/scalar", include_in_schema=False)
    async def scalar_html():
        return get_scalar_api_reference(
            openapi_url="/api/openapi.json",
            title=f"{settings.PROJECT_NAME} API Documentation",
        )

    @app.get("/health")
    async def health_check():
        """Health check endpoint with service status"""
        redis_status = "healthy"
        try:
            await cache.client.ping()
        except Exception:
            redis_status = "unhealthy"
        
        return {
            "status": "healthy" if redis_status == "healthy" else "degraded",
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "services": {
                "redis": redis_status,
                "api": "healthy"
            }
        }

    return app


app = create_app()
