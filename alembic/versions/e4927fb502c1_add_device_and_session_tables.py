"""add_device_and_session_tables

Revision ID: e4927fb502c1
Revises: d3836fa301f9
Create Date: 2025-12-08 10:00:00.000000

Migration to add device management and session tracking tables.
These tables support:
- Device registration and verification
- Active session management
- Refresh token tracking with rotation support
- Security features like device trust and session revocation

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4927fb502c1"
down_revision: Union[str, Sequence[str], None] = "d3836fa301f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add device and session tables."""

    # Create devices table
    op.create_table(
        "devices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        # Device identification
        sa.Column("device_id", sa.String(255), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("device_type", sa.String(50), nullable=True),
        # Platform info
        sa.Column("platform", sa.String(20), nullable=False, default="other"),
        sa.Column("os", sa.String(100), nullable=True),
        sa.Column("os_version", sa.String(50), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("browser", sa.String(100), nullable=True),
        sa.Column("browser_version", sa.String(50), nullable=True),
        # App info
        sa.Column("app_version", sa.String(50), nullable=True),
        # Push notifications
        sa.Column("fcm_token", sa.String(512), nullable=True),
        sa.Column("apns_token", sa.String(512), nullable=True),
        sa.Column("push_enabled", sa.Boolean(), nullable=False, default=False),
        # Fingerprinting
        sa.Column("browser_fingerprint", sa.String(255), nullable=True),
        sa.Column("hardware_fingerprint", sa.String(255), nullable=True),
        sa.Column("screen_resolution", sa.String(50), nullable=True),
        sa.Column("timezone", sa.String(100), nullable=True),
        # Device capabilities (JSON)
        sa.Column("capabilities", sa.Text(), nullable=True),
        # Status and verification
        sa.Column("status", sa.String(20), nullable=False, default="unverified"),
        sa.Column("verified", sa.Boolean(), nullable=False, default=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_code", sa.String(10), nullable=True),
        sa.Column("verification_code_expires", sa.DateTime(timezone=True), nullable=True),
        # Activity tracking
        sa.Column(
            "last_used_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("last_ip_address", sa.String(45), nullable=True),
        sa.Column("last_location", sa.String(255), nullable=True),
        # Trust and security
        sa.Column("is_trusted", sa.Boolean(), nullable=False, default=False),
        sa.Column("trust_score", sa.String(10), nullable=True),
        # Suspension/blocking
        sa.Column("inactive_reason", sa.String(255), nullable=True),
        sa.Column("blocked_reason", sa.String(255), nullable=True),
        sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
    )

    # Create indexes for devices
    op.create_index("ix_devices_user_device", "devices", ["user_id", "device_id"], unique=True)
    op.create_index("ix_devices_status", "devices", ["status"])
    op.create_index("ix_devices_platform", "devices", ["platform"])

    # Create user_sessions table
    op.create_table(
        "user_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "device_id",
            UUID(as_uuid=True),
            sa.ForeignKey("devices.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        # Token info
        sa.Column("refresh_token_hash", sa.String(255), nullable=True, index=True),
        sa.Column("access_token_jti", sa.String(255), nullable=True, unique=True),
        # Session metadata
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        # Parsed user agent info
        sa.Column("browser", sa.String(100), nullable=True),
        sa.Column("browser_version", sa.String(50), nullable=True),
        sa.Column("os", sa.String(100), nullable=True),
        sa.Column("os_version", sa.String(50), nullable=True),
        sa.Column("device_type", sa.String(50), nullable=True),
        # Location (from IP geolocation)
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("country_code", sa.String(10), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("latitude", sa.String(20), nullable=True),
        sa.Column("longitude", sa.String(20), nullable=True),
        # Session lifecycle
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "last_active_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        # Session status
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True, index=True),
        sa.Column("terminated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("termination_reason", sa.String(255), nullable=True),
        # Security flags
        sa.Column("is_suspicious", sa.Boolean(), nullable=False, default=False),
        sa.Column("suspicious_reason", sa.String(255), nullable=True),
        sa.Column("requires_verification", sa.Boolean(), nullable=False, default=False),
        # Login context
        sa.Column("login_method", sa.String(50), nullable=True),
        sa.Column("mfa_verified", sa.Boolean(), nullable=False, default=False),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
    )

    # Create indexes for user_sessions
    op.create_index("ix_sessions_user_active", "user_sessions", ["user_id", "is_active"])
    op.create_index("ix_sessions_expires", "user_sessions", ["expires_at"])

    # Create refresh_tokens table
    op.create_table(
        "refresh_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "session_id",
            UUID(as_uuid=True),
            sa.ForeignKey("user_sessions.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "device_id",
            UUID(as_uuid=True),
            sa.ForeignKey("devices.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        # Token data
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("token_family", sa.String(255), nullable=True, index=True),
        # Lifecycle
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        # Revocation
        sa.Column("is_revoked", sa.Boolean(), nullable=False, default=False, index=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.String(255), nullable=True),
        # Usage tracking
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("use_count", sa.String(10), nullable=False, default="0"),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
    )

    # Create indexes for refresh_tokens
    op.create_index("ix_refresh_tokens_family", "refresh_tokens", ["token_family", "is_revoked"])


def downgrade() -> None:
    """Downgrade schema - remove device and session tables."""

    # Drop indexes first
    op.drop_index("ix_refresh_tokens_family", table_name="refresh_tokens")
    op.drop_index("ix_sessions_expires", table_name="user_sessions")
    op.drop_index("ix_sessions_user_active", table_name="user_sessions")
    op.drop_index("ix_devices_platform", table_name="devices")
    op.drop_index("ix_devices_status", table_name="devices")
    op.drop_index("ix_devices_user_device", table_name="devices")

    # Drop tables in reverse order (due to foreign keys)
    op.drop_table("refresh_tokens")
    op.drop_table("user_sessions")
    op.drop_table("devices")
