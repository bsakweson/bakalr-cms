"""
OAuth2/OIDC Provider Service.
Makes CMS an identity provider for external applications.
Implements OAuth2 Authorization Code flow with PKCE and OpenID Connect.
"""

import base64
import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from backend.core.cache import CacheService
from backend.core.config import settings
from backend.models.oauth2 import (
    OAuth2AccessToken,
    OAuth2AuthorizationCode,
    OAuth2Client,
    OAuth2RefreshToken,
)
from backend.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class OAuth2ProviderService:
    """
    OAuth2/OIDC Provider implementation.
    Supports:
    - Authorization Code flow with PKCE
    - Refresh token rotation
    - OpenID Connect with ID tokens
    - Token introspection
    - Token revocation
    """

    # Authorization code TTL (10 minutes)
    AUTH_CODE_TTL = 600

    # Default token TTLs (overridable per client)
    DEFAULT_ACCESS_TOKEN_TTL = 3600  # 1 hour
    DEFAULT_REFRESH_TOKEN_TTL = 2592000  # 30 days
    DEFAULT_ID_TOKEN_TTL = 3600  # 1 hour

    def __init__(self, db: Session):
        self.db = db
        self.cache = CacheService()

    # === Client Management ===

    def create_client(
        self,
        organization_id: str,
        name: str,
        redirect_uris: List[str],
        client_type: str = "confidential",
        description: Optional[str] = None,
        logo_url: Optional[str] = None,
        grant_types: List[str] = None,
        allowed_scopes: str = "openid profile email",
        require_pkce: bool = True,
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Register a new OAuth2 client application.
        Returns client_id and client_secret (secret only shown once).
        """
        client_id = OAuth2Client.generate_client_id()
        client_secret = None
        client_secret_hash = None

        if client_type == "confidential":
            client_secret = OAuth2Client.generate_client_secret()
            client_secret_hash = pwd_context.hash(client_secret)

        grant_types = grant_types or ["authorization_code", "refresh_token"]

        client = OAuth2Client(
            organization_id=organization_id,
            client_id=client_id,
            client_secret_hash=client_secret_hash,
            name=name,
            description=description,
            logo_url=logo_url,
            client_type=client_type,
            grant_types=json.dumps(grant_types),
            redirect_uris=json.dumps(redirect_uris),
            allowed_scopes=allowed_scopes,
            require_pkce=require_pkce,
            created_by=created_by,
        )

        self.db.add(client)
        self.db.commit()
        self.db.refresh(client)

        return {
            "client_id": client_id,
            "client_secret": client_secret,  # Only shown once!
            "client": client,
            "message": (
                "Store the client_secret securely. It will not be shown again."
                if client_secret
                else None
            ),
        }

    def get_client(self, client_id: str) -> Optional[OAuth2Client]:
        """Get client by client_id"""
        return (
            self.db.query(OAuth2Client)
            .filter(
                OAuth2Client.client_id == client_id,
                OAuth2Client.is_active == True,
            )
            .first()
        )

    def validate_client_secret(self, client: OAuth2Client, client_secret: str) -> bool:
        """Validate client secret"""
        if not client.client_secret_hash:
            return False
        return pwd_context.verify(client_secret, client.client_secret_hash)

    def validate_redirect_uri(self, client: OAuth2Client, redirect_uri: str) -> bool:
        """Validate redirect URI against client's registered URIs"""
        allowed_uris = json.loads(client.redirect_uris)

        # Exact match required for security
        return redirect_uri in allowed_uris

    def validate_scopes(self, client: OAuth2Client, requested_scopes: str) -> str:
        """Validate and filter requested scopes against client's allowed scopes"""
        allowed = set(client.allowed_scopes.split())
        requested = set(requested_scopes.split()) if requested_scopes else allowed

        # Return intersection of requested and allowed
        valid_scopes = allowed & requested
        return " ".join(sorted(valid_scopes))

    # === Authorization Code Flow ===

    def create_authorization_code(
        self,
        client: OAuth2Client,
        user: User,
        redirect_uri: str,
        scopes: str,
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = None,
        nonce: Optional[str] = None,
    ) -> str:
        """
        Create an authorization code for the user.
        Returns the raw code (unhashed).
        """
        # Generate random code
        raw_code = secrets.token_urlsafe(48)
        code_hash = hashlib.sha256(raw_code.encode()).hexdigest()

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.AUTH_CODE_TTL)

        auth_code = OAuth2AuthorizationCode(
            code_hash=code_hash,
            client_id=client.id,
            user_id=user.id,
            redirect_uri=redirect_uri,
            scopes=scopes,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            nonce=nonce,
            expires_at=expires_at.isoformat(),
        )

        self.db.add(auth_code)
        self.db.commit()

        return raw_code

    def exchange_authorization_code(
        self,
        client: OAuth2Client,
        code: str,
        redirect_uri: str,
        code_verifier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for tokens.
        Validates PKCE if required.
        """
        code_hash = hashlib.sha256(code.encode()).hexdigest()

        auth_code = (
            self.db.query(OAuth2AuthorizationCode)
            .filter(
                OAuth2AuthorizationCode.code_hash == code_hash,
                OAuth2AuthorizationCode.client_id == client.id,
                OAuth2AuthorizationCode.is_used == False,
            )
            .first()
        )

        if not auth_code:
            raise ValueError("Invalid authorization code")

        if auth_code.is_expired:
            raise ValueError("Authorization code has expired")

        if auth_code.redirect_uri != redirect_uri:
            raise ValueError("Redirect URI mismatch")

        # Validate PKCE
        if auth_code.code_challenge:
            if not code_verifier:
                raise ValueError("Code verifier required")

            if not self._validate_pkce(
                code_verifier,
                auth_code.code_challenge,
                auth_code.code_challenge_method or "S256",
            ):
                raise ValueError("Invalid code verifier")
        elif client.require_pkce:
            raise ValueError("PKCE required for this client")

        # Mark code as used
        auth_code.is_used = True
        self.db.commit()

        # Get user
        user = self.db.query(User).filter(User.id == auth_code.user_id).first()
        if not user:
            raise ValueError("User not found")

        # Generate tokens
        access_token = self._create_access_token(client, user, auth_code.scopes)
        refresh_token = self._create_refresh_token(client, user, auth_code.scopes)

        result = {
            "access_token": access_token["token"],
            "token_type": "Bearer",
            "expires_in": int(client.access_token_ttl),
            "refresh_token": refresh_token["token"],
            "scope": auth_code.scopes,
        }

        # Add ID token for OIDC
        if "openid" in auth_code.scopes:
            id_token = self._create_id_token(client, user, auth_code.scopes, auth_code.nonce)
            result["id_token"] = id_token

        return result

    def _validate_pkce(self, verifier: str, challenge: str, method: str) -> bool:
        """Validate PKCE code verifier against challenge"""
        if method == "plain":
            return verifier == challenge
        elif method == "S256":
            computed = (
                base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
                .decode()
                .rstrip("=")
            )
            return computed == challenge
        return False

    # === Token Management ===

    def _create_access_token(
        self,
        client: OAuth2Client,
        user: User,
        scopes: str,
    ) -> Dict[str, str]:
        """Create and store an access token"""
        raw_token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        ttl = int(client.access_token_ttl)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

        access_token = OAuth2AccessToken(
            token_hash=token_hash,
            client_id=client.id,
            user_id=user.id,
            scopes=scopes,
            expires_at=expires_at.isoformat(),
        )

        self.db.add(access_token)
        self.db.commit()

        return {"token": raw_token, "expires_at": expires_at}

    def _create_refresh_token(
        self,
        client: OAuth2Client,
        user: User,
        scopes: str,
        parent_token_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """Create and store a refresh token"""
        raw_token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        ttl = int(client.refresh_token_ttl)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

        refresh_token = OAuth2RefreshToken(
            token_hash=token_hash,
            client_id=client.id,
            user_id=user.id,
            scopes=scopes,
            expires_at=expires_at.isoformat(),
            parent_token_id=parent_token_id,
        )

        self.db.add(refresh_token)
        self.db.commit()

        return {"token": raw_token, "expires_at": expires_at}

    def _create_id_token(
        self,
        client: OAuth2Client,
        user: User,
        scopes: str,
        nonce: Optional[str] = None,
    ) -> str:
        """Create an OpenID Connect ID token (JWT)"""
        now = datetime.now(timezone.utc)
        ttl = int(client.id_token_ttl)

        claims = {
            "iss": settings.BACKEND_URL or "https://cms.bakalr.com",
            "sub": str(user.id),
            "aud": client.client_id,
            "exp": now + timedelta(seconds=ttl),
            "iat": now,
            "auth_time": int(now.timestamp()),
        }

        if nonce:
            claims["nonce"] = nonce

        # Add profile claims if requested
        scope_set = set(scopes.split())

        if "profile" in scope_set:
            claims["name"] = f"{user.first_name or ''} {user.last_name or ''}".strip()
            if user.first_name:
                claims["given_name"] = user.first_name
            if user.last_name:
                claims["family_name"] = user.last_name
            if user.avatar_url:
                claims["picture"] = user.avatar_url

        if "email" in scope_set:
            claims["email"] = user.email
            claims["email_verified"] = user.is_email_verified

        # Sign with secret key
        return jwt.encode(claims, settings.SECRET_KEY, algorithm="HS256")

    def refresh_tokens(
        self,
        client: OAuth2Client,
        refresh_token: str,
        scopes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        Implements token rotation for security.
        """
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

        token_record = (
            self.db.query(OAuth2RefreshToken)
            .filter(
                OAuth2RefreshToken.token_hash == token_hash,
                OAuth2RefreshToken.client_id == client.id,
            )
            .first()
        )

        if not token_record:
            raise ValueError("Invalid refresh token")

        if not token_record.is_valid:
            # Token reuse detected - revoke entire family
            self._revoke_token_family(token_record.id)
            raise ValueError("Refresh token has been revoked or expired")

        # Get user
        user = self.db.query(User).filter(User.id == token_record.user_id).first()
        if not user or not user.is_active:
            raise ValueError("User not found or inactive")

        # Validate scope downgrade (can only request same or fewer scopes)
        if scopes:
            original_scopes = set(token_record.scopes.split())
            requested_scopes = set(scopes.split())
            if not requested_scopes.issubset(original_scopes):
                raise ValueError("Cannot request additional scopes during refresh")
            final_scopes = scopes
        else:
            final_scopes = token_record.scopes

        # Revoke old refresh token
        token_record.is_revoked = True
        token_record.revoked_at = datetime.now(timezone.utc).isoformat()

        # Create new tokens
        access_token = self._create_access_token(client, user, final_scopes)
        new_refresh_token = self._create_refresh_token(
            client,
            user,
            final_scopes,
            parent_token_id=str(token_record.id),
        )

        self.db.commit()

        return {
            "access_token": access_token["token"],
            "token_type": "Bearer",
            "expires_in": int(client.access_token_ttl),
            "refresh_token": new_refresh_token["token"],
            "scope": final_scopes,
        }

    def _revoke_token_family(self, token_id: str):
        """Revoke all tokens in a refresh token family (security measure)"""
        # This would recursively revoke all tokens that descended from or led to this token
        # For simplicity, we'll just revoke tokens with matching user/client
        token = self.db.query(OAuth2RefreshToken).filter(OAuth2RefreshToken.id == token_id).first()

        if token:
            self.db.query(OAuth2RefreshToken).filter(
                OAuth2RefreshToken.user_id == token.user_id,
                OAuth2RefreshToken.client_id == token.client_id,
            ).update(
                {
                    "is_revoked": True,
                    "revoked_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            self.db.commit()

    def revoke_token(self, token: str, token_type_hint: Optional[str] = None) -> bool:
        """
        Revoke an access or refresh token.
        Implements RFC 7009 Token Revocation.
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Try access token first (or if hinted)
        if token_type_hint in [None, "access_token"]:
            access_token = (
                self.db.query(OAuth2AccessToken)
                .filter(OAuth2AccessToken.token_hash == token_hash)
                .first()
            )

            if access_token:
                access_token.is_revoked = True
                access_token.revoked_at = datetime.now(timezone.utc).isoformat()
                self.db.commit()
                return True

        # Try refresh token
        if token_type_hint in [None, "refresh_token"]:
            refresh_token = (
                self.db.query(OAuth2RefreshToken)
                .filter(OAuth2RefreshToken.token_hash == token_hash)
                .first()
            )

            if refresh_token:
                refresh_token.is_revoked = True
                refresh_token.revoked_at = datetime.now(timezone.utc).isoformat()
                self.db.commit()
                return True

        return False

    def introspect_token(self, token: str, token_type_hint: Optional[str] = None) -> Dict[str, Any]:
        """
        Introspect a token.
        Implements RFC 7662 Token Introspection.
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Try access token first
        if token_type_hint in [None, "access_token"]:
            access_token = (
                self.db.query(OAuth2AccessToken)
                .filter(OAuth2AccessToken.token_hash == token_hash)
                .first()
            )

            if access_token:
                if not access_token.is_valid:
                    return {"active": False}

                client = self.get_client_by_id(access_token.client_id)

                return {
                    "active": True,
                    "scope": access_token.scopes,
                    "client_id": client.client_id if client else None,
                    "username": None,  # Could add username lookup
                    "token_type": "Bearer",
                    "exp": int(
                        datetime.fromisoformat(
                            access_token.expires_at.replace("Z", "+00:00")
                        ).timestamp()
                    ),
                    "iat": (
                        int(datetime.fromisoformat(access_token.created_at).timestamp())
                        if access_token.created_at
                        else None
                    ),
                    "sub": str(access_token.user_id) if access_token.user_id else None,
                    "aud": client.client_id if client else None,
                    "iss": settings.BACKEND_URL or "https://cms.bakalr.com",
                }

        return {"active": False}

    def get_client_by_id(self, internal_id: str) -> Optional[OAuth2Client]:
        """Get client by internal database ID"""
        return self.db.query(OAuth2Client).filter(OAuth2Client.id == internal_id).first()

    # === OIDC Discovery ===

    def get_openid_configuration(self) -> Dict[str, Any]:
        """
        Get OpenID Connect Discovery document.
        /.well-known/openid-configuration
        """
        issuer = settings.BACKEND_URL or "https://cms.bakalr.com"

        return {
            "issuer": issuer,
            "authorization_endpoint": f"{issuer}/api/v1/oauth/authorize",
            "token_endpoint": f"{issuer}/api/v1/oauth/token",
            "userinfo_endpoint": f"{issuer}/api/v1/oauth/userinfo",
            "jwks_uri": f"{issuer}/api/v1/oauth/.well-known/jwks.json",
            "revocation_endpoint": f"{issuer}/api/v1/oauth/revoke",
            "introspection_endpoint": f"{issuer}/api/v1/oauth/introspect",
            "end_session_endpoint": f"{issuer}/api/v1/oauth/logout",
            "scopes_supported": ["openid", "profile", "email", "offline_access"],
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["HS256"],
            "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
            "code_challenge_methods_supported": ["S256", "plain"],
            "claims_supported": [
                "iss",
                "sub",
                "aud",
                "exp",
                "iat",
                "auth_time",
                "nonce",
                "name",
                "given_name",
                "family_name",
                "email",
                "email_verified",
                "picture",
            ],
        }

    def get_userinfo(self, user: User, scopes: str) -> Dict[str, Any]:
        """
        Get OpenID Connect UserInfo.
        Returns claims based on granted scopes.
        """
        scope_set = set(scopes.split())

        userinfo = {
            "sub": str(user.id),
        }

        if "profile" in scope_set:
            name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            if name:
                userinfo["name"] = name
            if user.first_name:
                userinfo["given_name"] = user.first_name
            if user.last_name:
                userinfo["family_name"] = user.last_name
            if user.avatar_url:
                userinfo["picture"] = user.avatar_url

        if "email" in scope_set:
            userinfo["email"] = user.email
            userinfo["email_verified"] = user.is_email_verified

        return userinfo


def get_oauth2_provider_service(db: Session) -> OAuth2ProviderService:
    """Factory function to create OAuth2ProviderService"""
    return OAuth2ProviderService(db)
