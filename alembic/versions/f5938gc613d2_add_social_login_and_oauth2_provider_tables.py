"""add_social_login_and_oauth2_provider_tables

Revision ID: f5938gc613d2
Revises: e4927fb502c1
Create Date: 2025-12-08 14:00:00.000000

Migration to add social login (OAuth2 client) and OAuth2 provider tables.
These tables support:
- Social login identities (Google, Apple, Facebook, GitHub, Microsoft)
- OAuth2 client registration (for CMS as identity provider)
- Authorization codes for OAuth2 flow
- Access and refresh tokens for OAuth2

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f5938gc613d2"
down_revision: Union[str, Sequence[str], None] = "e4927fb502c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add social login and OAuth2 provider tables."""

    # Create social_identities table (OAuth2 client - for social login)
    op.create_table(
        "social_identities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # Provider info
        sa.Column("provider", sa.String(50), nullable=False, index=True),
        sa.Column("provider_user_id", sa.String(255), nullable=False, index=True),
        sa.Column("provider_email", sa.String(255), nullable=True),
        sa.Column("provider_name", sa.String(255), nullable=True),
        sa.Column("provider_avatar_url", sa.String(500), nullable=True),
        # OAuth2 tokens
        sa.Column("access_token", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.String(50), nullable=True),
        sa.Column("scopes", sa.String(500), nullable=True),
        # Provider-specific data
        sa.Column("provider_data", sa.Text(), nullable=True),
        # Status
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("last_login_at", sa.String(50), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.String(50), nullable=True),
        sa.Column("updated_at", sa.String(50), nullable=True),
    )

    # Unique constraint for provider + provider_user_id
    op.create_unique_constraint(
        "uq_social_identity_provider_user", "social_identities", ["provider", "provider_user_id"]
    )

    # Create oauth2_clients table (OAuth2 provider - CMS as IdP)
    op.create_table(
        "oauth2_clients",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # Client identification
        sa.Column("client_id", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("client_secret_hash", sa.String(255), nullable=True),
        # Client metadata
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        # Client configuration
        sa.Column("client_type", sa.String(20), nullable=False, default="confidential"),
        sa.Column(
            "grant_types",
            sa.String(500),
            nullable=False,
            default='["authorization_code", "refresh_token"]',
        ),
        sa.Column("response_types", sa.String(200), nullable=False, default='["code"]'),
        sa.Column("redirect_uris", sa.Text(), nullable=False),
        sa.Column("post_logout_redirect_uris", sa.Text(), nullable=True),
        sa.Column("allowed_scopes", sa.String(500), nullable=False, default="openid profile email"),
        sa.Column("require_pkce", sa.Boolean(), nullable=False, default=True),
        # Token settings
        sa.Column("access_token_ttl", sa.String(20), nullable=False, default="3600"),
        sa.Column("refresh_token_ttl", sa.String(20), nullable=False, default="2592000"),
        sa.Column("id_token_ttl", sa.String(20), nullable=False, default="3600"),
        # Status
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        # Audit
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        # Timestamps
        sa.Column("created_at", sa.String(50), nullable=True),
        sa.Column("updated_at", sa.String(50), nullable=True),
    )

    # Create oauth2_authorization_codes table
    op.create_table(
        "oauth2_authorization_codes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("code_hash", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column(
            "client_id",
            UUID(as_uuid=True),
            sa.ForeignKey("oauth2_clients.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # Code data
        sa.Column("redirect_uri", sa.String(2000), nullable=False),
        sa.Column("scopes", sa.String(500), nullable=False),
        sa.Column("code_challenge", sa.String(128), nullable=True),
        sa.Column("code_challenge_method", sa.String(10), nullable=True),
        sa.Column("nonce", sa.String(255), nullable=True),
        # Lifecycle
        sa.Column("expires_at", sa.String(50), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False, default=False),
        # Timestamps
        sa.Column("created_at", sa.String(50), nullable=True),
        sa.Column("updated_at", sa.String(50), nullable=True),
    )

    # Create oauth2_access_tokens table
    op.create_table(
        "oauth2_access_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("token_hash", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("token_type", sa.String(20), nullable=False, default="Bearer"),
        sa.Column(
            "client_id",
            UUID(as_uuid=True),
            sa.ForeignKey("oauth2_clients.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        # Token data
        sa.Column("scopes", sa.String(500), nullable=False),
        sa.Column("expires_at", sa.String(50), nullable=False),
        # Revocation
        sa.Column("is_revoked", sa.Boolean(), nullable=False, default=False),
        sa.Column("revoked_at", sa.String(50), nullable=True),
        # Refresh token link
        sa.Column("refresh_token_id", UUID(as_uuid=True), nullable=True, index=True),
        # Timestamps
        sa.Column("created_at", sa.String(50), nullable=True),
        sa.Column("updated_at", sa.String(50), nullable=True),
    )

    # Create oauth2_refresh_tokens table
    op.create_table(
        "oauth2_refresh_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("token_hash", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column(
            "client_id",
            UUID(as_uuid=True),
            sa.ForeignKey("oauth2_clients.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        # Token data
        sa.Column("scopes", sa.String(500), nullable=False),
        sa.Column("expires_at", sa.String(50), nullable=False),
        # Revocation
        sa.Column("is_revoked", sa.Boolean(), nullable=False, default=False),
        sa.Column("revoked_at", sa.String(50), nullable=True),
        # Rotation tracking
        sa.Column("parent_token_id", UUID(as_uuid=True), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.String(50), nullable=True),
        sa.Column("updated_at", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema - remove social login and OAuth2 provider tables."""

    # Drop tables in reverse order (due to foreign keys)
    op.drop_table("oauth2_refresh_tokens")
    op.drop_table("oauth2_access_tokens")
    op.drop_table("oauth2_authorization_codes")
    op.drop_table("oauth2_clients")
    op.drop_constraint("uq_social_identity_provider_user", "social_identities", type_="unique")
    op.drop_table("social_identities")
