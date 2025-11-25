"""
FastAPI application configuration and initialization
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from scalar_fastapi import get_scalar_api_reference
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException
from strawberry.fastapi import GraphQLRouter

from backend.api import api_router
from backend.core.cache import cache
from backend.core.config import settings
from backend.core.exceptions import (
    AppException,
    app_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from backend.core.query_optimization import setup_query_logging
from backend.core.rate_limit import limiter
from backend.core.versioning import VersioningMiddleware
from backend.db import engine
from backend.graphql.context import get_graphql_context
from backend.graphql.schema import schema
from backend.middleware.performance import PerformanceMiddleware
from backend.middleware.security import setup_security_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle events for the FastAPI application
    """
    # Startup
    print(f"🚀 Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    print(f"📝 Environment: {settings.ENVIRONMENT}")
    print(f"🔧 Debug mode: {settings.DEBUG}")

    # Setup query logging for performance monitoring
    if settings.DEBUG:
        print("📊 Setting up query performance logging...")
        setup_query_logging(engine)

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

    # Performance monitoring middleware
    app.add_middleware(PerformanceMiddleware)

    # Security middleware (headers, CSRF, validation)
    setup_security_middleware(app, settings.SECRET_KEY)

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
                "detail": str(exc.detail) if hasattr(exc, "detail") else None,
            },
            headers={"Retry-After": str(exc.detail) if hasattr(exc, "detail") else "60"},
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
        """
        Health check endpoint for container orchestration
        Returns basic health status - use for liveness probes
        """
        return {
            "status": "healthy",
            "version": settings.VERSION,
            "timestamp": "2025-11-25T10:30:00Z",
        }

    @app.get("/health/ready")
    async def readiness_check():
        """
        Readiness check endpoint with service dependencies
        Use for Kubernetes readiness probes
        """
        import datetime

        from sqlalchemy import text

        services = {}
        overall_status = "ready"

        # Check Redis
        try:
            await cache.client.ping()
            services["redis"] = {"status": "healthy", "latency_ms": 0}
        except Exception as e:
            services["redis"] = {"status": "unhealthy", "error": str(e)}
            overall_status = "not_ready"

        # Check Database
        try:
            from backend.db.session import SessionLocal

            db = SessionLocal()
            start_time = datetime.datetime.now()
            db.execute(text("SELECT 1"))
            latency = (datetime.datetime.now() - start_time).total_seconds() * 1000
            db.close()
            services["database"] = {"status": "healthy", "latency_ms": round(latency, 2)}
        except Exception as e:
            services["database"] = {"status": "unhealthy", "error": str(e)}
            overall_status = "not_ready"

        # Check Meilisearch (optional)
        try:
            from backend.core.config import settings as app_settings

            if hasattr(app_settings, "MEILI_HOST"):
                import httpx

                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{app_settings.MEILI_HOST}/health", timeout=2.0)
                    if response.status_code == 200:
                        services["search"] = {"status": "healthy"}
                    else:
                        services["search"] = {"status": "degraded", "code": response.status_code}
        except Exception as e:
            services["search"] = {"status": "unavailable", "error": str(e)}

        status_code = 200 if overall_status == "ready" else 503

        return JSONResponse(
            status_code=status_code,
            content={
                "status": overall_status,
                "version": settings.VERSION,
                "environment": settings.ENVIRONMENT,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "services": services,
            },
        )

    return app


app = create_app()
