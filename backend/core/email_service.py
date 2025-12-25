"""
Email service for sending transactional and notification emails.
Uses CMS content model for templates with full translation support.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from sqlalchemy.orm import Session

from backend.core.config import settings


class EmailService:
    """
    Email service with CMS template rendering and delivery tracking.
    All templates are stored as CMS content entries with translation support.

    Template keys used:
    - email_verification: Email verification for new users
    - welcome: Welcome email after registration
    - password_reset: Password reset request
    - device_verification: Device verification code
    - new_login_alert: New login from unknown device/location
    - content_digest: Content activity digest
    - notification: Generic notification
    - user_invitation: Invite user to organization
    """

    def __init__(self):
        # Configure FastAPI-Mail
        import os

        suppress_send = os.getenv("MAIL_SUPPRESS_SEND", "0") == "1"

        self.conf = ConnectionConfig(
            MAIL_USERNAME=settings.SMTP_USER,
            MAIL_PASSWORD=settings.SMTP_PASSWORD,
            MAIL_FROM=settings.SMTP_FROM,
            MAIL_PORT=settings.SMTP_PORT,
            MAIL_SERVER=settings.SMTP_HOST,
            MAIL_STARTTLS=settings.SMTP_TLS,
            MAIL_SSL_TLS=settings.SMTP_SSL,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True,
            SUPPRESS_SEND=suppress_send,
        )
        self.fastmail = FastMail(self.conf)

    async def send_email(
        self,
        db: Session,
        to_email: str,
        template_key: str,
        variables: Dict[str, Any],
        organization_id: int,
        locale: str = "en",
        user_id: Optional[int] = None,
    ):
        """
        Send email using CMS content-based template with translation support.

        Args:
            db: Database session
            to_email: Recipient email address
            template_key: CMS template key (e.g., 'device_verification', 'welcome')
            variables: Variables to substitute in template
            organization_id: Organization ID for multi-tenancy
            locale: Locale code for translation (e.g., 'en', 'es', 'fr')
            user_id: Optional user ID for tracking

        Raises:
            ValueError: If template not found in CMS
        """
        from backend.core.email_template_service import get_email_template_service

        try:
            print(f"📧 Preparing email to {to_email}...")
            print(f"   Template Key: {template_key}")
            print(f"   Locale: {locale}")
            print(f"   Organization: {organization_id}")

            # Get template service and render
            template_service = get_email_template_service(db, organization_id)
            rendered = template_service.render_template(template_key, variables, locale)

            if not rendered:
                print(f"   ❌ Template '{template_key}' not found in CMS")
                # In development/testing, skip email if template not found
                if settings.DEBUG or settings.ENVIRONMENT in ("development", "testing"):
                    print(f"   ⚠️ Skipping email (template missing, DEBUG mode)")
                    return {
                        "subject": f"[Missing Template: {template_key}]",
                        "html": f"<p>Email skipped - template '{template_key}' not found</p>",
                        "text": f"Email skipped - template '{template_key}' not found",
                        "skipped": True
                    }
                raise ValueError(
                    f"Email template '{template_key}' not found. "
                    "Please create it in CMS content with type 'email_template'."
                )

            # If email was skipped due to missing template, return early
            if rendered.get("skipped"):
                return rendered

            # Create message
            message = MessageSchema(
                subject=rendered["subject"],
                recipients=[to_email],
                body=rendered["html"],
                subtype=MessageType.html,
            )

            # Send email
            await self.fastmail.send_message(message)

            print(f"✓ Email sent successfully to {to_email}: {rendered['subject']}")
            return rendered

        except Exception as e:
            import traceback

            print(f"✗ Failed to send email to {to_email}: {e}")
            print(f"   Error type: {type(e).__name__}")
            traceback.print_exc()
            raise

    async def send_verification_email(
        self,
        db: Session,
        to_email: str,
        user_name: str,
        verification_token: str,
        organization_name: str,
        organization_id: int,
        locale: str = "en",
        user_id: Optional[int] = None,
    ):
        """Send email verification email to new user."""
        verification_url = f"{settings.FRONTEND_URL}/verify-email/{verification_token}"

        return await self.send_email(
            db=db,
            to_email=to_email,
            template_key="email_verification",
            variables={
                "user_name": user_name,
                "organization_name": organization_name,
                "verification_url": verification_url,
                "expiry_hours": 24,
                "year": datetime.now(timezone.utc).year,
            },
            organization_id=organization_id,
            locale=locale,
            user_id=user_id,
        )

    async def send_welcome_email(
        self,
        db: Session,
        to_email: str,
        user_name: str,
        organization_name: str,
        organization_id: int,
        locale: str = "en",
        user_id: Optional[int] = None,
    ):
        """Send welcome email to new user."""
        return await self.send_email(
            db=db,
            to_email=to_email,
            template_key="welcome",
            variables={
                "user_name": user_name,
                "organization_name": organization_name,
                "login_url": f"{settings.FRONTEND_URL}/login",
                "dashboard_url": f"{settings.FRONTEND_URL}/dashboard",
                "year": datetime.now(timezone.utc).year,
            },
            organization_id=organization_id,
            locale=locale,
            user_id=user_id,
        )

    async def send_password_reset_email(
        self,
        db: Session,
        to_email: str,
        user_name: str,
        reset_token: str,
        organization_id: int,
        locale: str = "en",
        user_id: Optional[int] = None,
    ):
        """Send password reset email."""
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{reset_token}"

        return await self.send_email(
            db=db,
            to_email=to_email,
            template_key="password_reset",
            variables={
                "user_name": user_name,
                "reset_url": reset_url,
                "expiry_hours": 24,
                "year": datetime.now(timezone.utc).year,
            },
            organization_id=organization_id,
            locale=locale,
            user_id=user_id,
        )

    async def send_device_verification_email(
        self,
        db: Session,
        to_email: str,
        user_name: str,
        device_name: str,
        verification_code: str,
        organization_id: int,
        locale: str = "en",
        expires_minutes: int = 15,
    ):
        """Send device verification code email."""
        return await self.send_email(
            db=db,
            to_email=to_email,
            template_key="device_verification",
            variables={
                "user_name": user_name,
                "device_name": device_name,
                "verification_code": verification_code,
                "expires_minutes": expires_minutes,
                "year": datetime.now(timezone.utc).year,
            },
            organization_id=organization_id,
            locale=locale,
        )

    async def send_new_login_alert_email(
        self,
        db: Session,
        to_email: str,
        user_name: str,
        device_info: str,
        location: str,
        ip_address: str,
        login_time: str,
        organization_id: int,
        locale: str = "en",
    ):
        """Send new login alert email."""
        return await self.send_email(
            db=db,
            to_email=to_email,
            template_key="new_login_alert",
            variables={
                "user_name": user_name,
                "device_info": device_info,
                "location": location,
                "ip_address": ip_address,
                "login_time": login_time,
                "year": datetime.now(timezone.utc).year,
            },
            organization_id=organization_id,
            locale=locale,
        )

    async def send_content_digest_email(
        self,
        db: Session,
        to_email: str,
        user_name: str,
        organization_name: str,
        content_summary: Dict[str, Any],
        organization_id: int,
        locale: str = "en",
        user_id: Optional[int] = None,
    ):
        """Send content digest email (daily/weekly)."""
        return await self.send_email(
            db=db,
            to_email=to_email,
            template_key="content_digest",
            variables={
                "user_name": user_name,
                "organization_name": organization_name,
                "content_summary": content_summary,
                "dashboard_url": f"{settings.FRONTEND_URL}/dashboard",
                "year": datetime.now(timezone.utc).year,
            },
            organization_id=organization_id,
            locale=locale,
            user_id=user_id,
        )

    async def send_notification_email(
        self,
        db: Session,
        to_email: str,
        user_name: str,
        notification_title: str,
        notification_message: str,
        action_url: Optional[str],
        organization_id: int,
        locale: str = "en",
        user_id: Optional[int] = None,
    ):
        """Send generic notification email."""
        return await self.send_email(
            db=db,
            to_email=to_email,
            template_key="notification",
            variables={
                "user_name": user_name,
                "notification_title": notification_title,
                "notification_message": notification_message,
                "action_url": action_url or "",
                "year": datetime.now(timezone.utc).year,
            },
            organization_id=organization_id,
            locale=locale,
            user_id=user_id,
        )

    async def send_invite_email(
        self,
        db: Session,
        to_email: str,
        user_name: str,
        inviter_name: str,
        organization_name: str,
        role_name: str,
        invite_token: str,
        organization_id: int,
        locale: str = "en",
        user_id: Optional[int] = None,
    ):
        """Send invitation email to join organization."""
        invite_url = f"{settings.FRONTEND_URL}/accept-invite/{invite_token}"

        return await self.send_email(
            db=db,
            to_email=to_email,
            template_key="user_invitation",
            variables={
                "user_name": user_name,
                "inviter_name": inviter_name,
                "organization_name": organization_name,
                "role_name": role_name,
                "invite_url": invite_url,
                "expiry_hours": 72,
                "year": datetime.now(timezone.utc).year,
            },
            organization_id=organization_id,
            locale=locale,
            user_id=user_id,
        )


# Global email service instance
email_service = EmailService()
