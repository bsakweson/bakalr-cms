"""
Kubernetes-optimized configuration with environment variable support
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


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
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")
    DEBUG: bool = Field(default=True, description="Enable debug mode")
    API_V1_PREFIX: str = Field(default="/api/v1", description="API version prefix")

    # CORS - Parse comma-separated string for Kubernetes ConfigMap
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000",
        description="Comma-separated list of allowed CORS origins"
    )

    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./bakalr_cms.db",
        description="Database connection URL. Format: postgresql://user:password@host:port/dbname"
    )
    DATABASE_ECHO: bool = Field(default=False, description="Log SQL queries")
    DATABASE_POOL_SIZE: int = Field(default=5, description="Database connection pool size")
    DATABASE_MAX_OVERFLOW: int = Field(default=10, description="Max connections beyond pool size")

    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    REDIS_MAX_CONNECTIONS: int = Field(default=10, description="Redis connection pool size")

    # Meilisearch
    MEILISEARCH_URL: str = Field(
        default="http://localhost:7700",
        description="Meilisearch server URL"
    )
    MEILISEARCH_API_KEY: str = Field(
        default="",
        description="Meilisearch API key (optional for development)"
    )

    # Security
    SECRET_KEY: str = Field(
        default="your-secret-key-change-this-in-production-min-32-chars",
        description="JWT secret key - MUST be changed in production"
    )
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Access token expiration in minutes")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="Refresh token expiration in days")

    # Celery
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1",
        description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/2",
        description="Celery result backend URL"
    )

    # File Upload & Storage
    UPLOAD_DIR: str = Field(
        default="uploads",
        description="Local storage directory (used with STORAGE_BACKEND=local)"
    )
    STORAGE_BACKEND: str = Field(
        default="local",
        description="Storage backend: 'local' or 's3'"
    )
    
    # S3 Storage (only used if STORAGE_BACKEND='s3')
    AWS_ACCESS_KEY_ID: str = Field(
        default="",
        description="AWS access key ID (use Kubernetes Secret)"
    )
    AWS_SECRET_ACCESS_KEY: str = Field(
        default="",
        description="AWS secret access key (use Kubernetes Secret)"
    )
    AWS_REGION: str = Field(
        default="us-east-1",
        description="AWS region"
    )
    S3_BUCKET_NAME: str = Field(
        default="",
        description="S3 bucket name"
    )
    S3_ENDPOINT_URL: str = Field(
        default="",
        description="Custom S3 endpoint for S3-compatible services (MinIO, etc.)"
    )
    S3_USE_SSL: bool = Field(
        default=True,
        description="Use SSL for S3 connections"
    )
    S3_PUBLIC_URL: str = Field(
        default="",
        description="Custom public URL for CDN (CloudFront, etc.)"
    )
    MAX_UPLOAD_SIZE: int = Field(
        default=10 * 1024 * 1024,
        description="Maximum file upload size in bytes (default: 10MB)"
    )

    # Translation
    GOOGLE_TRANSLATE_API_KEY: str = Field(
        default="",
        description="Google Translate API key (use Kubernetes Secret)"
    )
    DEEPL_API_KEY: str = Field(
        default="",
        description="DeepL API key (use Kubernetes Secret)"
    )
    DEFAULT_LANGUAGE: str = Field(
        default="en",
        description="Default language code"
    )

    # Pagination
    DEFAULT_PAGE_SIZE: int = Field(
        default=20,
        description="Default page size for list endpoints"
    )
    MAX_PAGE_SIZE: int = Field(
        default=100,
        description="Maximum allowed page size"
    )
    
    # Health Check
    HEALTH_CHECK_PATH: str = Field(
        default="/health",
        description="Health check endpoint path"
    )
    
    # Logging
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL"
    )
    LOG_FORMAT: str = Field(
        default="json",
        description="Log format: 'json' for production, 'console' for development"
    )
    
    # Two-Factor Authentication (2FA)
    TWO_FACTOR_ENABLED: bool = Field(
        default=True,
        description="Enable two-factor authentication support"
    )
    TWO_FACTOR_ISSUER_NAME: str = Field(
        default="Bakalr CMS",
        description="Issuer name displayed in authenticator apps"
    )
    TWO_FACTOR_CODE_VALIDITY_SECONDS: int = Field(
        default=30,
        description="TOTP code validity window in seconds"
    )
    TWO_FACTOR_BACKUP_CODES_COUNT: int = Field(
        default=10,
        description="Number of backup codes to generate"
    )
    TWO_FACTOR_ENFORCE_FOR_ADMINS: bool = Field(
        default=False,
        description="Require 2FA for admin roles"
    )
    
    # Email / SMTP Configuration
    SMTP_HOST: str = Field(
        default="localhost",
        description="SMTP server hostname"
    )
    SMTP_PORT: int = Field(
        default=587,
        description="SMTP server port (587 for TLS, 465 for SSL, 25 for plain)"
    )
    SMTP_USER: str = Field(
        default="",
        description="SMTP authentication username"
    )
    SMTP_PASSWORD: str = Field(
        default="",
        description="SMTP authentication password"
    )
    SMTP_FROM: str = Field(
        default="noreply@bakalr.cms",
        description="Default sender email address"
    )
    SMTP_TLS: bool = Field(
        default=True,
        description="Use STARTTLS (port 587)"
    )
    SMTP_SSL: bool = Field(
        default=False,
        description="Use SSL/TLS (port 465)"
    )
    
    # Notification Settings
    NOTIFICATIONS_ENABLED: bool = Field(
        default=True,
        description="Enable in-app notifications"
    )
    NOTIFICATION_EXPIRY_DAYS: int = Field(
        default=30,
        description="Days to keep notifications before auto-deletion"
    )
    EMAIL_NOTIFICATIONS_ENABLED: bool = Field(
        default=True,
        description="Enable email notifications"
    )
    
    # Frontend URL (for email links)
    FRONTEND_URL: str = Field(
        default="http://localhost:3000",
        description="Frontend application URL for email links"
    )
    TWO_FACTOR_ISSUER_NAME: str = Field(
        default="Bakalr CMS",
        description="Issuer name displayed in authenticator apps"
    )
    TWO_FACTOR_CODE_VALIDITY_SECONDS: int = Field(
        default=30,
        description="TOTP code validity period in seconds"
    )
    TWO_FACTOR_BACKUP_CODES_COUNT: int = Field(
        default=10,
        description="Number of backup codes to generate"
    )
    TWO_FACTOR_ENFORCE_FOR_ADMINS: bool = Field(
        default=False,
        description="Require 2FA for admin users"
    )
    
    # Content Templates
    CONTENT_TEMPLATES_ENABLED: bool = Field(
        default=True,
        description="Enable content templates and blueprints"
    )
    MAX_TEMPLATES_PER_TYPE: int = Field(
        default=50,
        description="Maximum number of templates per content type"
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
