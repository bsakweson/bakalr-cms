"""
Keycloak Authentication Plugin for Bakalr CMS

This module provides Keycloak JWT token validation, allowing the CMS to accept
tokens issued by Keycloak. This enables a unified authentication system where
Keycloak is the single identity provider.

Features:
- Validates Keycloak JWT tokens using JWKS (public keys)
- Maps Keycloak claims to CMS user model
- Auto-provisions CMS users on first access
- Auto-creates organizations based on tenant claims
- Supports role mapping from Keycloak realm/client roles

Usage:
    Set AUTH_PROVIDER=keycloak in environment variables and configure:
    - KEYCLOAK_SERVER_URL: Keycloak server URL
    - KEYCLOAK_REALM: Realm name
    - KEYCLOAK_CLIENT_ID: Client ID for this application
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError
from pydantic import BaseModel

from backend.core.config import settings

logger = logging.getLogger(__name__)


class KeycloakConfig(BaseModel):
    """Keycloak configuration"""

    server_url: str
    realm: str
    client_id: str
    client_secret: Optional[str] = None
    verify_ssl: bool = True

    @property
    def issuer(self) -> str:
        """Get the expected token issuer URL"""
        return f"{self.server_url}/realms/{self.realm}"

    @property
    def jwks_url(self) -> str:
        """Get the JWKS endpoint URL"""
        return f"{self.issuer}/protocol/openid-connect/certs"

    @property
    def token_endpoint(self) -> str:
        """Get the token endpoint URL"""
        return f"{self.issuer}/protocol/openid-connect/token"

    @property
    def userinfo_endpoint(self) -> str:
        """Get the userinfo endpoint URL"""
        return f"{self.issuer}/protocol/openid-connect/userinfo"


class KeycloakTokenData(BaseModel):
    """Parsed Keycloak token data"""

    sub: str  # Keycloak user ID (UUID)
    email: str
    email_verified: bool = False
    preferred_username: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    name: Optional[str] = None
    realm_roles: list[str] = []
    client_roles: list[str] = []
    tenant_id: Optional[str] = None  # Custom claim for multi-tenancy
    organization_name: Optional[str] = None  # Custom claim
    exp: Optional[int] = None
    iat: Optional[int] = None


class KeycloakAuthProvider:
    """
    Keycloak authentication provider for Bakalr CMS.

    Handles JWT token validation using Keycloak's JWKS endpoint.
    Caches public keys to minimize network calls.
    """

    def __init__(self, config: KeycloakConfig):
        self.config = config
        self._jwks_cache: Optional[Dict[str, Any]] = None
        self._jwks_cache_time: Optional[datetime] = None
        self._jwks_cache_ttl = 3600  # 1 hour

    async def get_jwks(self) -> Dict[str, Any]:
        """
        Fetch JWKS from Keycloak (with caching).

        Returns:
            JWKS response containing public keys
        """
        now = datetime.now(timezone.utc)

        # Check cache
        if (
            self._jwks_cache
            and self._jwks_cache_time
            and (now - self._jwks_cache_time).total_seconds() < self._jwks_cache_ttl
        ):
            return self._jwks_cache

        # Fetch fresh JWKS
        try:
            async with httpx.AsyncClient(verify=self.config.verify_ssl) as client:
                response = await client.get(self.config.jwks_url, timeout=10.0)
                response.raise_for_status()
                self._jwks_cache = response.json()
                self._jwks_cache_time = now
                logger.debug("Fetched fresh JWKS from Keycloak")
                return self._jwks_cache
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch JWKS from Keycloak: {e}")
            # Return cached if available, even if expired
            if self._jwks_cache:
                logger.warning("Using stale JWKS cache due to fetch failure")
                return self._jwks_cache
            raise

    def _get_signing_key(self, token: str, jwks: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get the signing key for a token from JWKS.

        Args:
            token: JWT token
            jwks: JWKS response

        Returns:
            Signing key dict or None
        """
        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            if not kid:
                logger.warning("Token has no 'kid' header")
                return None

            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    return key

            logger.warning(f"No matching key found for kid: {kid}")
            return None
        except JWTError as e:
            logger.error(f"Error parsing token header: {e}")
            return None

    async def verify_token(self, token: str) -> Optional[KeycloakTokenData]:
        """
        Verify a Keycloak JWT token.

        Args:
            token: JWT token string

        Returns:
            KeycloakTokenData if valid, None otherwise
        """
        try:
            # Get JWKS
            jwks = await self.get_jwks()

            # Get signing key
            signing_key = self._get_signing_key(token, jwks)
            if not signing_key:
                return None

            # Decode and verify token
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.config.client_id,
                issuer=self.config.issuer,
                options={
                    "verify_aud": True,
                    "verify_iss": True,
                    "verify_exp": True,
                },
            )

            # Extract roles from token
            realm_roles = []
            client_roles = []

            # Realm roles: realm_access.roles
            realm_access = payload.get("realm_access", {})
            realm_roles = realm_access.get("roles", [])

            # Client roles: resource_access.<client_id>.roles
            resource_access = payload.get("resource_access", {})
            client_access = resource_access.get(self.config.client_id, {})
            client_roles = client_access.get("roles", [])

            # Extract tenant info from custom claims
            tenant_id = payload.get("tenant_id") or payload.get("tenantId")
            organization_name = payload.get("organization_name") or payload.get("shop_name")

            return KeycloakTokenData(
                sub=payload.get("sub"),
                email=payload.get("email", ""),
                email_verified=payload.get("email_verified", False),
                preferred_username=payload.get("preferred_username"),
                given_name=payload.get("given_name"),
                family_name=payload.get("family_name"),
                name=payload.get("name"),
                realm_roles=realm_roles,
                client_roles=client_roles,
                tenant_id=tenant_id,
                organization_name=organization_name,
                exp=payload.get("exp"),
                iat=payload.get("iat"),
            )

        except ExpiredSignatureError:
            logger.debug("Token has expired")
            return None
        except JWTError as e:
            logger.warning(f"JWT verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error verifying token: {e}")
            return None

    def map_roles_to_cms(self, keycloak_data: KeycloakTokenData) -> list[str]:
        """
        Map Keycloak roles to CMS roles.

        Args:
            keycloak_data: Parsed Keycloak token data

        Returns:
            List of CMS role names
        """
        cms_roles = []
        all_roles = set(keycloak_data.realm_roles + keycloak_data.client_roles)

        # Role mapping (Keycloak -> CMS)
        role_mapping = {
            "admin": "admin",
            "super_admin": "super_admin",
            "manager": "admin",
            "editor": "editor",
            "author": "editor",
            "viewer": "viewer",
            "employee": "editor",
            "vendor": "editor",
            "owner": "admin",  # Shop owner = admin in CMS
        }

        for kc_role in all_roles:
            kc_role_lower = kc_role.lower()
            if kc_role_lower in role_mapping:
                cms_roles.append(role_mapping[kc_role_lower])

        # Default to viewer if no roles matched
        if not cms_roles:
            cms_roles = ["viewer"]

        return list(set(cms_roles))  # Remove duplicates


# Global Keycloak provider instance (lazily initialized)
_keycloak_provider: Optional[KeycloakAuthProvider] = None


def get_keycloak_config() -> Optional[KeycloakConfig]:
    """
    Get Keycloak configuration from settings.

    Returns:
        KeycloakConfig if Keycloak auth is enabled, None otherwise
    """
    if not getattr(settings, "AUTH_PROVIDER", "cms") == "keycloak":
        return None

    server_url = getattr(settings, "KEYCLOAK_SERVER_URL", "")
    realm = getattr(settings, "KEYCLOAK_REALM", "")
    client_id = getattr(settings, "KEYCLOAK_CLIENT_ID", "")

    if not all([server_url, realm, client_id]):
        logger.warning(
            "Keycloak auth enabled but missing configuration. "
            "Set KEYCLOAK_SERVER_URL, KEYCLOAK_REALM, and KEYCLOAK_CLIENT_ID."
        )
        return None

    return KeycloakConfig(
        server_url=server_url,
        realm=realm,
        client_id=client_id,
        client_secret=getattr(settings, "KEYCLOAK_CLIENT_SECRET", None),
        verify_ssl=getattr(settings, "KEYCLOAK_VERIFY_SSL", True),
    )


def get_keycloak_provider() -> Optional[KeycloakAuthProvider]:
    """
    Get the global Keycloak provider instance.

    Returns:
        KeycloakAuthProvider if configured, None otherwise
    """
    global _keycloak_provider

    if _keycloak_provider is not None:
        return _keycloak_provider

    config = get_keycloak_config()
    if config:
        _keycloak_provider = KeycloakAuthProvider(config)
        logger.info(f"Keycloak auth provider initialized for realm: {config.realm}")

    return _keycloak_provider


def is_keycloak_enabled() -> bool:
    """Check if Keycloak authentication is enabled"""
    return getattr(settings, "AUTH_PROVIDER", "cms") == "keycloak"
