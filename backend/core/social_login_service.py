"""
OAuth2 Social Login Service.
Handles authentication with Google, Apple, Facebook, GitHub, and Microsoft.
"""

import json
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from backend.core.cache import CacheService
from backend.core.config import settings
from backend.models.social_identity import SocialIdentity


class SocialProvider(str, Enum):
    """Supported social login providers"""

    GOOGLE = "google"
    APPLE = "apple"
    FACEBOOK = "facebook"
    GITHUB = "github"
    MICROSOFT = "microsoft"


@dataclass
class SocialUserInfo:
    """User information from social provider"""

    provider: SocialProvider
    provider_user_id: str
    email: Optional[str]
    name: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    avatar_url: Optional[str]
    email_verified: bool
    raw_data: Dict[str, Any]


@dataclass
class OAuthTokens:
    """OAuth2 token response"""

    access_token: str
    refresh_token: Optional[str]
    token_type: str
    expires_in: Optional[int]
    scope: Optional[str]
    id_token: Optional[str] = None


class OAuthProviderBase(ABC):
    """Abstract base class for OAuth2 providers"""

    provider: SocialProvider

    @abstractmethod
    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """Generate the authorization URL for the provider"""
        pass

    @abstractmethod
    async def exchange_code(self, code: str, redirect_uri: str) -> OAuthTokens:
        """Exchange authorization code for tokens"""
        pass

    @abstractmethod
    async def get_user_info(self, access_token: str) -> SocialUserInfo:
        """Get user information using the access token"""
        pass


class GoogleOAuthProvider(OAuthProviderBase):
    """Google OAuth2 provider"""

    provider = SocialProvider.GOOGLE

    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    def __init__(self):
        self.client_id = getattr(settings, "GOOGLE_CLIENT_ID", None)
        self.client_secret = getattr(settings, "GOOGLE_CLIENT_SECRET", None)

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> OAuthTokens:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            return OAuthTokens(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token"),
                token_type=data["token_type"],
                expires_in=data.get("expires_in"),
                scope=data.get("scope"),
                id_token=data.get("id_token"),
            )

    async def get_user_info(self, access_token: str) -> SocialUserInfo:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            return SocialUserInfo(
                provider=self.provider,
                provider_user_id=data["id"],
                email=data.get("email"),
                name=data.get("name"),
                first_name=data.get("given_name"),
                last_name=data.get("family_name"),
                avatar_url=data.get("picture"),
                email_verified=data.get("verified_email", False),
                raw_data=data,
            )


class AppleOAuthProvider(OAuthProviderBase):
    """Apple Sign In provider"""

    provider = SocialProvider.APPLE

    AUTH_URL = "https://appleid.apple.com/auth/authorize"
    TOKEN_URL = "https://appleid.apple.com/auth/token"

    def __init__(self):
        self.client_id = getattr(settings, "APPLE_CLIENT_ID", None)
        self.team_id = getattr(settings, "APPLE_TEAM_ID", None)
        self.key_id = getattr(settings, "APPLE_KEY_ID", None)
        self.private_key = getattr(settings, "APPLE_PRIVATE_KEY", None)

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.team_id and self.key_id and self.private_key)

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "name email",
            "state": state,
            "response_mode": "form_post",
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> OAuthTokens:
        # Apple requires a client_secret JWT signed with your private key
        # This is a simplified version - production needs PyJWT
        client_secret = self._generate_client_secret()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            return OAuthTokens(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token"),
                token_type=data["token_type"],
                expires_in=data.get("expires_in"),
                scope=None,
                id_token=data.get("id_token"),
            )

    def _generate_client_secret(self) -> str:
        """Generate Apple client_secret JWT"""
        # Note: Full implementation requires PyJWT with ES256 signing
        # This would typically look like:
        # import jwt
        # now = datetime.now(timezone.utc)
        # payload = {
        #     "iss": self.team_id,
        #     "iat": now,
        #     "exp": now + timedelta(days=180),
        #     "aud": "https://appleid.apple.com",
        #     "sub": self.client_id,
        # }
        # return jwt.encode(payload, self.private_key, algorithm="ES256", headers={"kid": self.key_id})
        raise NotImplementedError("Apple Sign In requires PyJWT for client_secret generation")

    async def get_user_info(self, access_token: str) -> SocialUserInfo:
        # Apple doesn't have a userinfo endpoint - data comes from id_token
        # The id_token is decoded during token exchange
        raise NotImplementedError(
            "Apple user info is extracted from id_token during token exchange"
        )


class FacebookOAuthProvider(OAuthProviderBase):
    """Facebook OAuth2 provider"""

    provider = SocialProvider.FACEBOOK

    AUTH_URL = "https://www.facebook.com/v18.0/dialog/oauth"
    TOKEN_URL = "https://graph.facebook.com/v18.0/oauth/access_token"
    USERINFO_URL = "https://graph.facebook.com/v18.0/me"

    def __init__(self):
        self.client_id = getattr(settings, "FACEBOOK_CLIENT_ID", None)
        self.client_secret = getattr(settings, "FACEBOOK_CLIENT_SECRET", None)

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "email,public_profile",
            "state": state,
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> OAuthTokens:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.TOKEN_URL,
                params={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            return OAuthTokens(
                access_token=data["access_token"],
                refresh_token=None,  # Facebook doesn't provide refresh tokens
                token_type="Bearer",
                expires_in=data.get("expires_in"),
                scope=None,
            )

    async def get_user_info(self, access_token: str) -> SocialUserInfo:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.USERINFO_URL,
                params={
                    "fields": "id,name,email,first_name,last_name,picture.type(large)",
                    "access_token": access_token,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            avatar_url = None
            if "picture" in data and "data" in data["picture"]:
                avatar_url = data["picture"]["data"].get("url")

            return SocialUserInfo(
                provider=self.provider,
                provider_user_id=data["id"],
                email=data.get("email"),
                name=data.get("name"),
                first_name=data.get("first_name"),
                last_name=data.get("last_name"),
                avatar_url=avatar_url,
                email_verified=True,  # Facebook emails are verified
                raw_data=data,
            )


class GitHubOAuthProvider(OAuthProviderBase):
    """GitHub OAuth2 provider"""

    provider = SocialProvider.GITHUB

    AUTH_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    USERINFO_URL = "https://api.github.com/user"
    EMAILS_URL = "https://api.github.com/user/emails"

    def __init__(self):
        self.client_id = getattr(settings, "GITHUB_CLIENT_ID", None)
        self.client_secret = getattr(settings, "GITHUB_CLIENT_SECRET", None)

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "scope": "read:user user:email",
            "state": state,
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> OAuthTokens:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                headers={"Accept": "application/json"},
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            return OAuthTokens(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token"),
                token_type=data["token_type"],
                expires_in=data.get("expires_in"),
                scope=data.get("scope"),
            )

    async def get_user_info(self, access_token: str) -> SocialUserInfo:
        async with httpx.AsyncClient() as client:
            # Get user profile
            response = await client.get(
                self.USERINFO_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            # Get primary email
            email = data.get("email")
            email_verified = False

            if not email:
                # Fetch emails separately
                emails_response = await client.get(
                    self.EMAILS_URL,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                    timeout=30.0,
                )
                if emails_response.status_code == 200:
                    emails = emails_response.json()
                    for e in emails:
                        if e.get("primary"):
                            email = e.get("email")
                            email_verified = e.get("verified", False)
                            break

            # Parse name
            name = data.get("name") or data.get("login")
            first_name, last_name = None, None
            if name and " " in name:
                parts = name.split(" ", 1)
                first_name = parts[0]
                last_name = parts[1]
            else:
                first_name = name

            return SocialUserInfo(
                provider=self.provider,
                provider_user_id=str(data["id"]),
                email=email,
                name=name,
                first_name=first_name,
                last_name=last_name,
                avatar_url=data.get("avatar_url"),
                email_verified=email_verified,
                raw_data=data,
            )


class MicrosoftOAuthProvider(OAuthProviderBase):
    """Microsoft OAuth2 provider"""

    provider = SocialProvider.MICROSOFT

    AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    USERINFO_URL = "https://graph.microsoft.com/v1.0/me"

    def __init__(self):
        self.client_id = getattr(settings, "MICROSOFT_CLIENT_ID", None)
        self.client_secret = getattr(settings, "MICROSOFT_CLIENT_SECRET", None)

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile User.Read",
            "state": state,
            "response_mode": "query",
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> OAuthTokens:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            return OAuthTokens(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token"),
                token_type=data["token_type"],
                expires_in=data.get("expires_in"),
                scope=data.get("scope"),
                id_token=data.get("id_token"),
            )

    async def get_user_info(self, access_token: str) -> SocialUserInfo:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            return SocialUserInfo(
                provider=self.provider,
                provider_user_id=data["id"],
                email=data.get("mail") or data.get("userPrincipalName"),
                name=data.get("displayName"),
                first_name=data.get("givenName"),
                last_name=data.get("surname"),
                avatar_url=None,  # Microsoft Graph requires separate call for photo
                email_verified=True,  # Microsoft emails are verified
                raw_data=data,
            )


class SocialLoginService:
    """
    Main service for handling social login flows.
    Manages OAuth2 state, token exchange, and user linking.
    """

    # State token TTL (10 minutes)
    STATE_TTL = 600

    def __init__(self, db: Session):
        self.db = db
        self.cache = CacheService()
        self.providers: Dict[SocialProvider, OAuthProviderBase] = {
            SocialProvider.GOOGLE: GoogleOAuthProvider(),
            SocialProvider.FACEBOOK: FacebookOAuthProvider(),
            SocialProvider.GITHUB: GitHubOAuthProvider(),
            SocialProvider.MICROSOFT: MicrosoftOAuthProvider(),
            SocialProvider.APPLE: AppleOAuthProvider(),
        }

    def get_available_providers(self) -> list:
        """Get list of configured providers"""
        available = []
        for provider, handler in self.providers.items():
            if hasattr(handler, "is_configured") and handler.is_configured:
                available.append(
                    {
                        "provider": provider.value,
                        "name": provider.value.title(),
                    }
                )
        return available

    def generate_state(
        self, user_id: Optional[str] = None, redirect_url: Optional[str] = None
    ) -> str:
        """Generate and store OAuth2 state token"""
        state = secrets.token_urlsafe(32)
        state_data = {
            "user_id": user_id,  # For linking to existing account
            "redirect_url": redirect_url,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.cache.set(f"oauth_state:{state}", state_data, ttl=self.STATE_TTL)
        return state

    def validate_state(self, state: str) -> Optional[Dict[str, Any]]:
        """Validate and consume OAuth2 state token"""
        state_data = self.cache.get(f"oauth_state:{state}")
        if state_data:
            self.cache.delete(f"oauth_state:{state}")
        return state_data

    def get_authorization_url(
        self,
        provider: SocialProvider,
        redirect_uri: str,
        user_id: Optional[str] = None,
        final_redirect_url: Optional[str] = None,
    ) -> str:
        """Generate authorization URL for a provider"""
        handler = self.providers.get(provider)
        if not handler:
            raise ValueError(f"Unknown provider: {provider}")

        if hasattr(handler, "is_configured") and not handler.is_configured:
            raise ValueError(f"Provider {provider} is not configured")

        state = self.generate_state(user_id, final_redirect_url)
        return handler.get_authorization_url(state, redirect_uri)

    async def handle_callback(
        self,
        provider: SocialProvider,
        code: str,
        state: str,
        redirect_uri: str,
    ) -> Dict[str, Any]:
        """
        Handle OAuth2 callback - exchange code, get user info, and create/link identity.
        Returns dict with user_info, tokens, identity, and state_data.
        """
        handler = self.providers.get(provider)
        if not handler:
            raise ValueError(f"Unknown provider: {provider}")

        # Validate state
        state_data = self.validate_state(state)
        if not state_data:
            raise ValueError("Invalid or expired OAuth2 state")

        # Exchange code for tokens
        tokens = await handler.exchange_code(code, redirect_uri)

        # Get user info
        user_info = await handler.get_user_info(tokens.access_token)

        # Find or create social identity
        identity = self._find_identity(provider, user_info.provider_user_id)

        if identity:
            # Update existing identity
            identity.access_token = tokens.access_token
            identity.refresh_token = tokens.refresh_token
            if tokens.expires_in:
                identity.token_expires_at = (
                    datetime.now(timezone.utc) + timedelta(seconds=tokens.expires_in)
                ).isoformat()
            identity.last_login_at = datetime.now(timezone.utc).isoformat()
            identity.provider_data = json.dumps(user_info.raw_data)
            self.db.commit()

        return {
            "user_info": user_info,
            "tokens": tokens,
            "identity": identity,
            "state_data": state_data,
            "is_new": identity is None,
        }

    def _find_identity(
        self,
        provider: SocialProvider,
        provider_user_id: str,
    ) -> Optional[SocialIdentity]:
        """Find existing social identity"""
        return (
            self.db.query(SocialIdentity)
            .filter(
                SocialIdentity.provider == provider.value,
                SocialIdentity.provider_user_id == provider_user_id,
                SocialIdentity.is_active == True,
            )
            .first()
        )

    def create_identity(
        self,
        user_id: str,
        provider: SocialProvider,
        user_info: SocialUserInfo,
        tokens: OAuthTokens,
    ) -> SocialIdentity:
        """Create new social identity linked to a user"""
        identity = SocialIdentity(
            user_id=user_id,
            provider=provider.value,
            provider_user_id=user_info.provider_user_id,
            provider_email=user_info.email,
            provider_name=user_info.name,
            provider_avatar_url=user_info.avatar_url,
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            scopes=tokens.scope,
            provider_data=json.dumps(user_info.raw_data),
            last_login_at=datetime.now(timezone.utc).isoformat(),
        )

        if tokens.expires_in:
            identity.token_expires_at = (
                datetime.now(timezone.utc) + timedelta(seconds=tokens.expires_in)
            ).isoformat()

        self.db.add(identity)
        self.db.commit()
        self.db.refresh(identity)

        return identity

    def get_user_identities(self, user_id: str) -> list:
        """Get all social identities for a user"""
        return (
            self.db.query(SocialIdentity)
            .filter(
                SocialIdentity.user_id == user_id,
                SocialIdentity.is_active == True,
            )
            .all()
        )

    def unlink_identity(self, user_id: str, provider: SocialProvider) -> bool:
        """Unlink a social identity from a user"""
        identity = (
            self.db.query(SocialIdentity)
            .filter(
                SocialIdentity.user_id == user_id,
                SocialIdentity.provider == provider.value,
            )
            .first()
        )

        if identity:
            identity.is_active = False
            self.db.commit()
            return True
        return False


def get_social_login_service(db: Session) -> SocialLoginService:
    """Factory function to create SocialLoginService"""
    return SocialLoginService(db)
