"""
Kubernetes-optimized configuration with environment variable support
"""

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with Kubernetes/container support

    All settings can be overridden via environment variables.
    Environment variables take precedence over .env file values.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_prefix="",  # No prefix, use exact variable names
    )

    # Project metadata
    PROJECT_NAME: str = Field(default="Bakalr CMS", description="Project name")
    VERSION: str = Field(default="0.1.0", description="API version")
    ENVIRONMENT: str = Field(
        default="development", description="Environment: development, staging, production"
    )
    DEBUG: bool = Field(default=True, description="Enable debug mode")
    API_V1_PREFIX: str = Field(default="/api/v1", description="API version prefix")

    # CORS - Parse comma-separated string for Kubernetes ConfigMap
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000",
        description="Comma-separated list of allowed CORS origins",
    )

    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./bakalr_cms.db",
        description="Database connection URL. Format: postgresql://user:password@host:port/dbname",
    )
    DATABASE_ECHO: bool = Field(default=False, description="Log SQL queries")
    DATABASE_POOL_SIZE: int = Field(default=5, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=10, description="Max connections beyond pool size")

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    REDIS_MAX_CONNECTIONS: int = Field(default=10, description="Redis connection pool size")

    # Meilisearch
    MEILISEARCH_URL: str = Field(
        default="http://localhost:7700", description="Meilisearch server URL"
    )
    MEILISEARCH_API_KEY: str = Field(
        default="", description="Meilisearch API key (optional for development)"
    )

    # Authentication Provider
    AUTH_PROVIDER: str = Field(
        default="cms",
        description="Authentication provider: 'cms' (built-in JWT) or 'keycloak' (external IdP)",
    )

    # Security (for built-in CMS auth)
    SECRET_KEY: str = Field(
        default="your-secret-key-change-this-in-production-min-32-chars",
        description="Secret key for general encryption - MUST be changed in production",
    )
    ALGORITHM: str = Field(default="RS256", description="JWT algorithm (RS256 recommended)")
    JWT_ISSUER: str = Field(
        default="http://localhost:8000",
        description="JWT issuer URL - should match the CMS backend URL",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, description="Access token expiration in minutes"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7, description="Refresh token expiration in days"
    )

    # Keycloak Configuration (when AUTH_PROVIDER=keycloak)
    KEYCLOAK_SERVER_URL: str = Field(
        default="", description="Keycloak server URL (e.g., http://localhost:8080)"
    )
    KEYCLOAK_REALM: str = Field(default="", description="Keycloak realm name")
    KEYCLOAK_CLIENT_ID: str = Field(
        default="", description="Keycloak client ID for this application"
    )
    KEYCLOAK_CLIENT_SECRET: str = Field(
        default="", description="Keycloak client secret (optional, for confidential clients)"
    )
    KEYCLOAK_VERIFY_SSL: bool = Field(
        default=True, description="Verify SSL certificates when connecting to Keycloak"
    )

    # Celery
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1", description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/2", description="Celery result backend URL"
    )

    # File Upload & Storage
    UPLOAD_DIR: str = Field(
        default="uploads", description="Local storage directory (used with STORAGE_BACKEND=local)"
    )
    STORAGE_BACKEND: str = Field(default="local", description="Storage backend: 'local' or 's3'")

    # S3 Storage (only used if STORAGE_BACKEND='s3')
    AWS_ACCESS_KEY_ID: str = Field(
        default="", description="AWS access key ID (use Kubernetes Secret)"
    )
    AWS_SECRET_ACCESS_KEY: str = Field(
        default="", description="AWS secret access key (use Kubernetes Secret)"
    )
    AWS_REGION: str = Field(default="us-east-1", description="AWS region")
    S3_BUCKET_NAME: str = Field(default="", description="S3 bucket name")
    S3_ENDPOINT_URL: str = Field(
        default="", description="Custom S3 endpoint for S3-compatible services (MinIO, etc.)"
    )
    S3_USE_SSL: bool = Field(default=True, description="Use SSL for S3 connections")
    S3_PUBLIC_URL: str = Field(
        default="", description="Custom public URL for CDN (CloudFront, etc.)"
    )
    MAX_UPLOAD_SIZE: int = Field(
        default=10 * 1024 * 1024, description="Maximum file upload size in bytes (default: 10MB)"
    )

    # Translation
    TRANSLATION_PROVIDER: str = Field(
        default="libretranslate", description="Translation provider: libretranslate, google, deepl"
    )
    LIBRETRANSLATE_URL: str = Field(
        default="http://localhost:5001", description="LibreTranslate API URL"
    )
    LIBRETRANSLATE_API_KEY: str = Field(
        default="", description="LibreTranslate API key (optional, leave empty for local instance)"
    )
    GOOGLE_TRANSLATE_API_KEY: str = Field(
        default="", description="Google Translate API key (use Kubernetes Secret)"
    )
    DEEPL_API_KEY: str = Field(default="", description="DeepL API key (use Kubernetes Secret)")
    DEEPL_API_URL: str = Field(
        default="https://api-free.deepl.com/v2/translate",
        description="DeepL API URL (use api-free.deepl.com for free tier)",
    )
    DEFAULT_LANGUAGE: str = Field(default="en", description="Default language code")

    # Pagination
    DEFAULT_PAGE_SIZE: int = Field(default=20, description="Default page size for list endpoints")
    MAX_PAGE_SIZE: int = Field(default=100, description="Maximum allowed page size")

    # Health Check
    HEALTH_CHECK_PATH: str = Field(default="/health", description="Health check endpoint path")

    # Logging
    LOG_LEVEL: str = Field(
        default="INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL"
    )
    LOG_FORMAT: str = Field(
        default="json", description="Log format: 'json' for production, 'console' for development"
    )

    # Two-Factor Authentication (2FA)
    TWO_FACTOR_ENABLED: bool = Field(
        default=True, description="Enable two-factor authentication support"
    )
    TWO_FACTOR_ISSUER_NAME: str = Field(
        default="Bakalr CMS", description="Issuer name displayed in authenticator apps"
    )
    TWO_FACTOR_CODE_VALIDITY_SECONDS: int = Field(
        default=30, description="TOTP code validity window in seconds"
    )
    TWO_FACTOR_BACKUP_CODES_COUNT: int = Field(
        default=10, description="Number of backup codes to generate"
    )
    TWO_FACTOR_ENFORCE_FOR_ADMINS: bool = Field(
        default=False, description="Require 2FA for admin roles"
    )

    # Email / SMTP Configuration
    SMTP_HOST: str = Field(default="localhost", description="SMTP server hostname")
    SMTP_PORT: int = Field(
        default=587, description="SMTP server port (587 for TLS, 465 for SSL, 25 for plain)"
    )
    SMTP_USER: str = Field(default="", description="SMTP authentication username")
    SMTP_PASSWORD: str = Field(default="", description="SMTP authentication password")
    SMTP_FROM: str = Field(default="noreply@bakalr.cms", description="Default sender email address")
    SMTP_TLS: bool = Field(default=True, description="Use STARTTLS (port 587)")
    SMTP_SSL: bool = Field(default=False, description="Use SSL/TLS (port 465)")

    # Notification Settings
    NOTIFICATIONS_ENABLED: bool = Field(default=True, description="Enable in-app notifications")
    NOTIFICATION_EXPIRY_DAYS: int = Field(
        default=30, description="Days to keep notifications before auto-deletion"
    )
    EMAIL_NOTIFICATIONS_ENABLED: bool = Field(
        default=True, description="Enable email notifications"
    )

    # Frontend URL (for email links)
    FRONTEND_URL: str = Field(
        default="http://localhost:3000", description="Frontend application URL for email links"
    )
    BACKEND_URL: str = Field(
        default="http://localhost:8000", description="Backend API URL for OAuth2 issuer"
    )
    TWO_FACTOR_ISSUER_NAME: str = Field(
        default="Bakalr CMS", description="Issuer name displayed in authenticator apps"
    )
    TWO_FACTOR_CODE_VALIDITY_SECONDS: int = Field(
        default=30, description="TOTP code validity period in seconds"
    )
    TWO_FACTOR_BACKUP_CODES_COUNT: int = Field(
        default=10, description="Number of backup codes to generate"
    )
    TWO_FACTOR_ENFORCE_FOR_ADMINS: bool = Field(
        default=False, description="Require 2FA for admin users"
    )

    # Social Login - Google
    GOOGLE_CLIENT_ID: str = Field(default="", description="Google OAuth2 client ID")
    GOOGLE_CLIENT_SECRET: str = Field(default="", description="Google OAuth2 client secret")

    # Social Login - Apple
    APPLE_CLIENT_ID: str = Field(default="", description="Apple Sign In client ID (Services ID)")
    APPLE_TEAM_ID: str = Field(default="", description="Apple Developer Team ID")
    APPLE_KEY_ID: str = Field(default="", description="Apple Sign In Key ID")
    APPLE_PRIVATE_KEY: str = Field(default="", description="Apple Sign In private key (PEM)")

    # Social Login - Facebook
    FACEBOOK_CLIENT_ID: str = Field(default="", description="Facebook OAuth2 app ID")
    FACEBOOK_CLIENT_SECRET: str = Field(default="", description="Facebook OAuth2 app secret")

    # Social Login - GitHub
    GITHUB_CLIENT_ID: str = Field(default="", description="GitHub OAuth2 client ID")
    GITHUB_CLIENT_SECRET: str = Field(default="", description="GitHub OAuth2 client secret")

    # Social Login - Microsoft
    MICROSOFT_CLIENT_ID: str = Field(default="", description="Microsoft OAuth2 client ID")
    MICROSOFT_CLIENT_SECRET: str = Field(default="", description="Microsoft OAuth2 client secret")

    # Push Notifications - Firebase Cloud Messaging
    FCM_API_KEY: str = Field(default="", description="Firebase Cloud Messaging API key")
    FCM_PROJECT_ID: str = Field(default="", description="Firebase project ID")

    # Push Notifications - Apple Push Notification Service
    APNS_KEY_ID: str = Field(default="", description="APNS authentication key ID")
    APNS_TEAM_ID: str = Field(default="", description="Apple Developer Team ID for APNS")
    APNS_BUNDLE_ID: str = Field(default="", description="iOS app bundle ID")
    APNS_PRODUCTION: bool = Field(default=False, description="Use APNS production server")

    # Push Notifications - Gotify (self-hosted)
    GOTIFY_SERVER_URL: str = Field(default="", description="Gotify server URL")
    GOTIFY_APP_TOKEN: str = Field(default="", description="Gotify application token")

    # Push Notifications - Ntfy
    NTFY_SERVER_URL: str = Field(default="https://ntfy.sh", description="Ntfy server URL")
    NTFY_DEFAULT_TOPIC: str = Field(default="", description="Default ntfy topic")
    NTFY_ACCESS_TOKEN: str = Field(default="", description="Ntfy access token (optional)")

    # Geo-Location
    IPINFO_TOKEN: str = Field(default="", description="ipinfo.io API token (optional)")

    # GraphQL Settings
    GRAPHQL_MAX_DEPTH: int = Field(
        default=10, description="Maximum query depth for GraphQL to prevent abuse"
    )
    GRAPHQL_MAX_COMPLEXITY: int = Field(
        default=1000, description="Maximum query complexity for GraphQL to prevent abuse"
    )
    GRAPHQL_TIMEOUT_SECONDS: int = Field(
        default=30, description="Maximum execution time for GraphQL queries in seconds"
    )

    # Content Templates
    CONTENT_TEMPLATES_ENABLED: bool = Field(
        default=True, description="Enable content templates and blueprints"
    )
    MAX_TEMPLATES_PER_TYPE: int = Field(
        default=50, description="Maximum number of templates per content type"
    )

    # Rate Limiting - Simple default for all endpoints
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_DEFAULT: str = Field(
        default="1000/hour;100/minute", description="Default rate limit for all endpoints"
    )
    RATE_LIMIT_GRAPHQL: str = Field(
        default="1000/hour;100/minute", description="Rate limit for GraphQL endpoints"
    )

    def get_cors_origins_list(self) -> List[str]:
        """Parse CORS_ORIGINS string into list"""
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return self.CORS_ORIGINS

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT.lower() == "development"


# Singleton instance
settings = Settings()


settings = Settings()
