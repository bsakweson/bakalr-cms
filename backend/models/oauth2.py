"""
OAuth2 Client model for OAuth2/OIDC Provider functionality.
Allows CMS to act as an identity provider for external applications.
"""

import secrets
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from backend.db.base import Base
from backend.models.base import GUID, IDMixin, TimestampMixin


class OAuth2Client(Base, IDMixin, TimestampMixin):
    """
    OAuth2 Client application registration.
    External applications (boutique-ui, mobile apps) register as clients
    to authenticate users via CMS.
    """

    __tablename__ = "oauth2_clients"

    # Organization this client belongs to
    organization_id = Column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Client identification
    client_id = Column(String(64), unique=True, nullable=False, index=True)
    client_secret_hash = Column(String(255), nullable=True)  # Hashed, null for public clients

    # Client metadata
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)

    # Client type
    client_type = Column(String(20), default="confidential", nullable=False)  # confidential, public

    # Allowed grant types (JSON array)
    grant_types = Column(
        String(500), default='["authorization_code", "refresh_token"]', nullable=False
    )

    # Allowed response types (JSON array)
    response_types = Column(String(200), default='["code"]', nullable=False)

    # Redirect URIs (JSON array)
    redirect_uris = Column(Text, nullable=False)  # JSON array of allowed redirect URIs

    # Post-logout redirect URIs (JSON array)
    post_logout_redirect_uris = Column(Text, nullable=True)

    # Allowed scopes (space-separated)
    allowed_scopes = Column(String(500), default="openid profile email", nullable=False)

    # PKCE requirement
    require_pkce = Column(Boolean, default=True, nullable=False)

    # Token settings
    access_token_ttl = Column(String, default="3600", nullable=False)  # seconds
    refresh_token_ttl = Column(String, default="2592000", nullable=False)  # 30 days
    id_token_ttl = Column(String, default="3600", nullable=False)  # 1 hour

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Audit
    created_by = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    organization = relationship("Organization", backref="oauth2_clients")
    authorization_codes = relationship(
        "OAuth2AuthorizationCode",
        back_populates="client",
        cascade="all, delete-orphan",
    )
    access_tokens = relationship(
        "OAuth2AccessToken",
        back_populates="client",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<OAuth2Client(client_id='{self.client_id}', name='{self.name}')>"

    @staticmethod
    def generate_client_id() -> str:
        """Generate a random client ID"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def generate_client_secret() -> str:
        """Generate a random client secret"""
        return secrets.token_urlsafe(48)


class OAuth2AuthorizationCode(Base, IDMixin, TimestampMixin):
    """
    OAuth2 authorization code issued during the authorization flow.
    Short-lived, exchanged for access tokens.
    """

    __tablename__ = "oauth2_authorization_codes"

    # Code value (hashed)
    code_hash = Column(String(255), unique=True, nullable=False, index=True)

    # Client this code was issued to
    client_id = Column(
        GUID(),
        ForeignKey("oauth2_clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # User who authorized
    user_id = Column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Redirect URI used
    redirect_uri = Column(String(2000), nullable=False)

    # Scopes granted
    scopes = Column(String(500), nullable=False)

    # PKCE code challenge
    code_challenge = Column(String(128), nullable=True)
    code_challenge_method = Column(String(10), nullable=True)  # S256 or plain

    # Nonce for OIDC
    nonce = Column(String(255), nullable=True)

    # Expiration
    expires_at = Column(String, nullable=False)  # ISO datetime

    # Used flag (codes are single-use)
    is_used = Column(Boolean, default=False, nullable=False)

    # Relationships
    client = relationship("OAuth2Client", back_populates="authorization_codes")
    user = relationship("User", backref="oauth2_authorization_codes")

    def __repr__(self):
        return f"<OAuth2AuthorizationCode(client_id={self.client_id}, user_id={self.user_id})>"

    @property
    def is_expired(self) -> bool:
        """Check if the code has expired"""
        expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) > expires


class OAuth2AccessToken(Base, IDMixin, TimestampMixin):
    """
    OAuth2 access token issued to clients.
    Used to access protected resources on behalf of the user.
    """

    __tablename__ = "oauth2_access_tokens"

    # Token value (hashed)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)

    # Token type (always Bearer for now)
    token_type = Column(String(20), default="Bearer", nullable=False)

    # Client this token was issued to
    client_id = Column(
        GUID(),
        ForeignKey("oauth2_clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # User this token represents (null for client credentials)
    user_id = Column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Scopes granted
    scopes = Column(String(500), nullable=False)

    # Expiration
    expires_at = Column(String, nullable=False)  # ISO datetime

    # Revocation
    is_revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(String, nullable=True)  # ISO datetime

    # Associated refresh token ID
    refresh_token_id = Column(GUID(), nullable=True, index=True)

    # Relationships
    client = relationship("OAuth2Client", back_populates="access_tokens")
    user = relationship("User", backref="oauth2_access_tokens")

    def __repr__(self):
        return f"<OAuth2AccessToken(client_id={self.client_id}, user_id={self.user_id})>"

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired"""
        expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) > expires

    @property
    def is_valid(self) -> bool:
        """Check if the token is valid (not expired or revoked)"""
        return not self.is_expired and not self.is_revoked


class OAuth2RefreshToken(Base, IDMixin, TimestampMixin):
    """
    OAuth2 refresh token for obtaining new access tokens.
    Long-lived, can be rotated or revoked.
    """

    __tablename__ = "oauth2_refresh_tokens"

    # Token value (hashed)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)

    # Client this token was issued to
    client_id = Column(
        GUID(),
        ForeignKey("oauth2_clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # User this token represents
    user_id = Column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Scopes (to maintain scope across refresh)
    scopes = Column(String(500), nullable=False)

    # Expiration
    expires_at = Column(String, nullable=False)  # ISO datetime

    # Revocation
    is_revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(String, nullable=True)  # ISO datetime

    # Rotation tracking
    parent_token_id = Column(GUID(), nullable=True)  # Previous token in chain

    # Relationships
    client = relationship("OAuth2Client", backref="oauth2_refresh_tokens")
    user = relationship("User", backref="oauth2_refresh_tokens")

    def __repr__(self):
        return f"<OAuth2RefreshToken(client_id={self.client_id}, user_id={self.user_id})>"

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired"""
        expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) > expires

    @property
    def is_valid(self) -> bool:
        """Check if the token is valid (not expired or revoked)"""
        return not self.is_expired and not self.is_revoked
