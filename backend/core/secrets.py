"""
Secrets management for Bakalr CMS

Handles secure loading and validation of secrets from environment variables.
Supports integration with AWS Secrets Manager, HashiCorp Vault, etc.
"""

import json
import logging
import os
from functools import lru_cache
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class SecretsManager:
    """
    Secure secrets management

    Loads secrets from environment variables with support for
    external secret stores (AWS Secrets Manager, Vault, etc.)
    """

    def __init__(self, environment: str = "development"):
        self.environment = environment
        self._secrets_cache: Dict[str, str] = {}

    def get_secret(
        self, key: str, default: Optional[str] = None, required: bool = False
    ) -> Optional[str]:
        """
        Get secret value

        Args:
            key: Secret key name
            default: Default value if secret not found
            required: Raise exception if secret not found

        Returns:
            Secret value or default

        Raises:
            ValueError: If required secret is missing
        """
        # Check cache first
        if key in self._secrets_cache:
            return self._secrets_cache[key]

        # Try environment variable
        value = os.getenv(key, default)

        if value is None and required:
            raise ValueError(f"Required secret '{key}' not found in environment")

        # Cache the value
        if value is not None:
            self._secrets_cache[key] = value

        return value

    def get_database_url(self) -> str:
        """Get database connection URL"""
        return self.get_secret("DATABASE_URL", required=True)

    def get_secret_key(self) -> str:
        """Get application secret key"""
        secret_key = self.get_secret("SECRET_KEY", required=True)

        # Validate secret key strength
        if len(secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")

        return secret_key

    def get_jwt_secret(self) -> str:
        """Get JWT signing secret"""
        return self.get_secret("JWT_SECRET_KEY", required=True)

    def get_redis_url(self) -> Optional[str]:
        """Get Redis connection URL"""
        return self.get_secret("REDIS_URL", default="redis://localhost:6379/0")

    def get_smtp_settings(self) -> Dict[str, Any]:
        """Get SMTP configuration for email"""
        return {
            "host": self.get_secret("SMTP_HOST", "localhost"),
            "port": int(self.get_secret("SMTP_PORT", "587")),
            "username": self.get_secret("SMTP_USERNAME"),
            "password": self.get_secret("SMTP_PASSWORD"),
            "use_tls": self.get_secret("SMTP_USE_TLS", "true").lower() == "true",
            "from_email": self.get_secret("SMTP_FROM_EMAIL", "noreply@bakalr.cms"),
        }

    def get_aws_credentials(self) -> Dict[str, str]:
        """Get AWS credentials for S3"""
        return {
            "access_key_id": self.get_secret("AWS_ACCESS_KEY_ID", ""),
            "secret_access_key": self.get_secret("AWS_SECRET_ACCESS_KEY", ""),
            "region": self.get_secret("AWS_REGION", "us-east-1"),
            "s3_bucket": self.get_secret("AWS_S3_BUCKET", ""),
        }

    def validate_secrets(self) -> bool:
        """
        Validate all required secrets are present

        Returns:
            True if all required secrets are valid

        Raises:
            ValueError: If validation fails
        """
        required_secrets = [
            "SECRET_KEY",
            "JWT_SECRET_KEY",
            "DATABASE_URL",
        ]

        missing = []
        for secret in required_secrets:
            if not self.get_secret(secret):
                missing.append(secret)

        if missing:
            raise ValueError(f"Missing required secrets: {', '.join(missing)}")

        # Validate secret key strength
        secret_key = self.get_secret("SECRET_KEY")
        if len(secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long for security")

        jwt_secret = self.get_secret("JWT_SECRET_KEY")
        if len(jwt_secret) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long for security")

        logger.info("✅ All required secrets validated successfully")
        return True


class AWSSecretsManager(SecretsManager):
    """
    AWS Secrets Manager integration

    Loads secrets from AWS Secrets Manager service.
    Requires boto3 to be installed.
    """

    def __init__(self, environment: str = "development", region: str = "us-east-1"):
        super().__init__(environment)
        self.region = region
        self._client = None

    def _get_client(self):
        """Get boto3 Secrets Manager client"""
        if self._client is None:
            try:
                import boto3

                self._client = boto3.client("secretsmanager", region_name=self.region)
            except ImportError:
                raise ImportError(
                    "boto3 is required for AWS Secrets Manager. Install with: pip install boto3"
                )
        return self._client

    def get_secret(
        self, key: str, default: Optional[str] = None, required: bool = False
    ) -> Optional[str]:
        """
        Get secret from AWS Secrets Manager

        Falls back to environment variable if AWS secret not found.
        """
        # Try AWS Secrets Manager first
        try:
            client = self._get_client()
            response = client.get_secret_value(SecretId=f"{self.environment}/{key}")

            # Parse JSON secret if applicable
            if "SecretString" in response:
                secret = response["SecretString"]
                try:
                    secret_dict = json.loads(secret)
                    if isinstance(secret_dict, dict) and "value" in secret_dict:
                        return secret_dict["value"]
                    return secret
                except json.JSONDecodeError:
                    return secret
        except Exception as e:
            logger.warning(f"Failed to load secret '{key}' from AWS: {e}")

        # Fall back to environment variable
        return super().get_secret(key, default, required)


class VaultSecretsManager(SecretsManager):
    """
    HashiCorp Vault integration

    Loads secrets from Vault service.
    Requires hvac to be installed.
    """

    def __init__(
        self,
        environment: str = "development",
        vault_url: Optional[str] = None,
        vault_token: Optional[str] = None,
    ):
        super().__init__(environment)
        self.vault_url = vault_url or os.getenv("VAULT_ADDR", "http://localhost:8200")
        self.vault_token = vault_token or os.getenv("VAULT_TOKEN")
        self._client = None

    def _get_client(self):
        """Get hvac Vault client"""
        if self._client is None:
            try:
                import hvac

                self._client = hvac.Client(url=self.vault_url, token=self.vault_token)
                if not self._client.is_authenticated():
                    raise ValueError("Vault authentication failed")
            except ImportError:
                raise ImportError(
                    "hvac is required for Vault integration. Install with: pip install hvac"
                )
        return self._client

    def get_secret(
        self, key: str, default: Optional[str] = None, required: bool = False
    ) -> Optional[str]:
        """
        Get secret from Vault

        Falls back to environment variable if Vault secret not found.
        """
        # Try Vault first
        try:
            client = self._get_client()
            secret_path = f"secret/data/{self.environment}/{key}"
            response = client.secrets.kv.v2.read_secret_version(path=secret_path)

            if response and "data" in response and "data" in response["data"]:
                return response["data"]["data"].get("value")
        except Exception as e:
            logger.warning(f"Failed to load secret '{key}' from Vault: {e}")

        # Fall back to environment variable
        return super().get_secret(key, default, required)


@lru_cache()
def get_secrets_manager() -> SecretsManager:
    """
    Get secrets manager instance

    Returns appropriate secrets manager based on environment configuration.
    """
    environment = os.getenv("ENVIRONMENT", "development")
    secrets_backend = os.getenv("SECRETS_BACKEND", "env")

    if secrets_backend == "aws":
        region = os.getenv("AWS_REGION", "us-east-1")
        return AWSSecretsManager(environment=environment, region=region)
    elif secrets_backend == "vault":
        return VaultSecretsManager(environment=environment)
    else:
        # Default to environment variables
        return SecretsManager(environment=environment)


# Convenience functions
def get_secret(key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    """Get secret value"""
    return get_secrets_manager().get_secret(key, default, required)


def validate_secrets() -> bool:
    """Validate all required secrets"""
    return get_secrets_manager().validate_secrets()
