"""
Social Login (OAuth2 Identity) model.
Stores linked social accounts (Google, Apple, Facebook, etc.) for users.
"""

from sqlalchemy import Boolean, Column, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from backend.db.base import Base
from backend.models.base import GUID, IDMixin, TimestampMixin


class SocialIdentity(Base, IDMixin, TimestampMixin):
    """
    Social/OAuth2 identity linked to a user account.
    Allows users to sign in via Google, Apple, Facebook, GitHub, etc.
    """

    __tablename__ = "social_identities"

    # User this identity belongs to
    user_id = Column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # OAuth2 Provider (google, apple, facebook, github, microsoft)
    provider = Column(String(50), nullable=False, index=True)

    # Provider's unique user ID
    provider_user_id = Column(String(255), nullable=False, index=True)

    # Provider's email (may differ from user's primary email)
    provider_email = Column(String(255), nullable=True)

    # Display name from provider
    provider_name = Column(String(255), nullable=True)

    # Profile picture URL from provider
    provider_avatar_url = Column(String(500), nullable=True)

    # OAuth2 tokens (encrypted in production)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(String, nullable=True)  # ISO datetime string

    # Token scopes granted
    scopes = Column(String(500), nullable=True)  # Space-separated scopes

    # Provider-specific data (JSON)
    provider_data = Column(Text, nullable=True)  # Raw profile data from provider

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Last used for login
    last_login_at = Column(String, nullable=True)  # ISO datetime string

    # Relationships
    user = relationship("User", backref="social_identities")

    # Constraints
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_social_identity_provider_user"),
    )

    def __repr__(self):
        return f"<SocialIdentity(user_id={self.user_id}, provider='{self.provider}', provider_user_id='{self.provider_user_id}')>"
