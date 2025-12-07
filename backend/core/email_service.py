"""
Email service for sending transactional and notification emails.
Uses FastAPI-Mail with Jinja2 templates and queue support.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from jinja2 import Environment, FileSystemLoader, select_autoescape

from backend.core.config import settings


class EmailService:
    """
    Email service with template rendering and delivery tracking.
    Supports transactional emails, notifications, and bulk sending.
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
            SUPPRESS_SEND=suppress_send,  # Disable email sending in tests
            TEMPLATE_FOLDER=Path(__file__).parent.parent / "templates" / "emails",
        )
        self.fastmail = FastMail(self.conf)

        # Configure Jinja2 for templates
        template_dir = Path(__file__).parent.parent / "templates" / "emails"
        template_dir.mkdir(parents=True, exist_ok=True)

        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    async def send_email(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        template_vars: Dict[str, Any],
        organization_id: int,
        user_id: Optional[int] = None,
        attachments: Optional[List[str]] = None,
    ):
        """
        Send email with template rendering.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            template_name: Name of Jinja2 template (e.g., "welcome.html")
            template_vars: Variables to pass to template
            organization_id: Organization ID for multi-tenancy
            user_id: Optional user ID
            attachments: Optional list of file paths
        """
        try:
            print(f"📧 Preparing to send email to {to_email}...")
            print(f"   SMTP Host: {settings.SMTP_HOST}:{settings.SMTP_PORT}")
            print(f"   SMTP User: {settings.SMTP_USER}")
            print(f"   Template: {template_name}")

            # Render template
            template = self.jinja_env.get_template(template_name)
            html_content = template.render(**template_vars)

            # Create message
            message = MessageSchema(
                subject=subject, recipients=[to_email], body=html_content, subtype=MessageType.html
            )

            # Send email
            await self.fastmail.send_message(message)

            print(f"✓ Email sent successfully to {to_email}: {subject}")

        except Exception as e:
            import traceback

            print(f"✗ Failed to send email to {to_email}: {e}")
            print(f"   Error type: {type(e).__name__}")
            traceback.print_exc()
            raise

    async def send_verification_email(
        self,
        to_email: str,
        user_name: str,
        verification_token: str,
        organization_name: str,
        organization_id: int,
        user_id: int,
    ):
        """Send email verification email to new user"""
        verification_url = f"{settings.FRONTEND_URL}/verify-email/{verification_token}"

        return await self.send_email(
            to_email=to_email,
            subject=f"Verify Your Email - {organization_name}",
            template_name="verify_email.html",
            template_vars={
                "user_name": user_name,
                "organization_name": organization_name,
                "verification_url": verification_url,
                "expiry_hours": 24,
                "year": datetime.now(timezone.utc).year,
            },
            organization_id=organization_id,
            user_id=user_id,
        )

    async def send_welcome_email(
        self,
        to_email: str,
        user_name: str,
        organization_name: str,
        organization_id: int,
        user_id: int,
    ):
        """Send welcome email to new user"""
        return await self.send_email(
            to_email=to_email,
            subject=f"Welcome to {organization_name} - Bakalr CMS",
            template_name="welcome.html",
            template_vars={
                "user_name": user_name,
                "organization_name": organization_name,
                "login_url": f"{settings.FRONTEND_URL}/login",
                "dashboard_url": f"{settings.FRONTEND_URL}/dashboard",
                "year": datetime.now(timezone.utc).year,
            },
            organization_id=organization_id,
            user_id=user_id,
        )

    async def send_password_reset_email(
        self, to_email: str, user_name: str, reset_token: str, organization_id: int, user_id: int
    ):
        """Send password reset email"""
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{reset_token}"

        return await self.send_email(
            to_email=to_email,
            subject="Reset Your Password - Bakalr CMS",
            template_name="password_reset.html",
            template_vars={
                "user_name": user_name,
                "reset_url": reset_url,
                "expiry_hours": 24,
                "year": datetime.now(timezone.utc).year,
            },
            organization_id=organization_id,
            user_id=user_id,
        )

    async def send_content_digest_email(
        self,
        to_email: str,
        user_name: str,
        organization_name: str,
        content_summary: Dict[str, Any],
        organization_id: int,
        user_id: int,
    ):
        """Send content digest email (daily/weekly)"""
        return await self.send_email(
            to_email=to_email,
            subject=f"Content Digest - {organization_name}",
            template_name="content_digest.html",
            template_vars={
                "user_name": user_name,
                "organization_name": organization_name,
                "content_summary": content_summary,
                "dashboard_url": f"{settings.FRONTEND_URL}/dashboard",
                "year": datetime.now(timezone.utc).year,
            },
            organization_id=organization_id,
            user_id=user_id,
        )

    async def send_notification_email(
        self,
        to_email: str,
        user_name: str,
        notification_title: str,
        notification_message: str,
        action_url: Optional[str],
        organization_id: int,
        user_id: int,
    ):
        """Send generic notification email"""
        return await self.send_email(
            to_email=to_email,
            subject=f"Notification: {notification_title}",
            template_name="notification.html",
            template_vars={
                "user_name": user_name,
                "notification_title": notification_title,
                "notification_message": notification_message,
                "action_url": action_url,
                "year": datetime.now(timezone.utc).year,
            },
            organization_id=organization_id,
            user_id=user_id,
        )


# Global email service instance
email_service = EmailService()
