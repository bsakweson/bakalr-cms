"""
Email Template Service - Fetches email templates from CMS content system.
Uses the same content model as frontend with full translation support.
"""

import json
import re
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from backend.core.cache import RedisCache
from backend.models.content import ContentEntry, ContentType
from backend.models.translation import Locale, Translation

# Cache TTL for email templates (1 hour)
EMAIL_TEMPLATE_CACHE_TTL = 3600


class EmailTemplateService:
    """
    Service for fetching and rendering email templates from CMS content.
    Supports auto-translation via CMS translation system.
    """

    def __init__(self, db: Session, organization_id: int):
        self.db = db
        self.organization_id = organization_id
        self.cache = RedisCache()

    def _get_email_template_type(self) -> Optional[ContentType]:
        """Get the email_template content type for this organization."""
        return (
            self.db.query(ContentType)
            .filter(
                ContentType.api_id == "email_template",
                ContentType.organization_id == self.organization_id,
            )
            .first()
        )

    def _get_template_entry(self, template_key: str) -> Optional[ContentEntry]:
        """Get email template content entry by template_key."""
        content_type = self._get_email_template_type()
        if not content_type:
            return None

        # Find entry where data.template_key matches
        entries = (
            self.db.query(ContentEntry)
            .filter(
                ContentEntry.content_type_id == content_type.id,
                ContentEntry.status == "published",
            )
            .all()
        )

        for entry in entries:
            try:
                data = json.loads(entry.data) if isinstance(entry.data, str) else entry.data
                if data.get("template_key") == template_key:
                    return entry
            except (json.JSONDecodeError, TypeError):
                continue

        return None

    def _get_translated_data(self, entry: ContentEntry, locale_code: str) -> Dict[str, Any]:
        """Get translated data for an entry, falling back to default."""
        # Get default data
        try:
            default_data = json.loads(entry.data) if isinstance(entry.data, str) else entry.data
        except (json.JSONDecodeError, TypeError):
            default_data = {}

        if locale_code == "en":
            return default_data

        # Try to find translation
        locale = (
            self.db.query(Locale)
            .filter(
                Locale.code == locale_code,
                Locale.organization_id == self.organization_id,
                Locale.is_enabled == True,
            )
            .first()
        )

        if not locale:
            return default_data

        translation = (
            self.db.query(Translation)
            .filter(
                Translation.content_entry_id == entry.id,
                Translation.locale_id == locale.id,
                Translation.status == "published",
            )
            .first()
        )

        if translation and translation.translated_data:
            try:
                translated = (
                    json.loads(translation.translated_data)
                    if isinstance(translation.translated_data, str)
                    else translation.translated_data
                )
                # Merge: translated values override defaults
                return {**default_data, **translated}
            except (json.JSONDecodeError, TypeError):
                pass

        return default_data

    def get_template(self, template_key: str, locale: str = "en") -> Optional[Dict[str, Any]]:
        """
        Get email template by key with locale support.

        Args:
            template_key: Unique template identifier (e.g., 'device_verification')
            locale: Locale code (e.g., 'en', 'es', 'fr')

        Returns:
            Dict with template fields or None if not found
        """
        cache_key = f"email_template:{self.organization_id}:{template_key}:{locale}"

        # Try cache first (using sync method)
        cached = self.cache.get_json_sync(cache_key)
        if cached:
            return cached

        entry = self._get_template_entry(template_key)
        if not entry:
            return None

        data = self._get_translated_data(entry, locale)

        # Cache the result (using sync method)
        self.cache.set_sync(cache_key, data, ttl=EMAIL_TEMPLATE_CACHE_TTL)

        return data

    def render_template(
        self, template_key: str, variables: Dict[str, Any], locale: str = "en"
    ) -> Optional[Dict[str, str]]:
        """
        Render email template with variables.

        Args:
            template_key: Unique template identifier
            variables: Dict of variable names to values
            locale: Locale code

        Returns:
            Dict with 'subject', 'html', 'text' or None if template not found
        """
        template = self.get_template(template_key, locale)
        if not template:
            return None

        def replace_vars(text: str) -> str:
            """Replace {{variable}} placeholders with values."""
            if not text:
                return ""
            for key, value in variables.items():
                text = text.replace(f"{{{{{key}}}}}", str(value))
            # Also support {variable} format
            for key, value in variables.items():
                text = re.sub(rf"\{{{key}\}}", str(value), text)
            return text

        subject = replace_vars(template.get("subject", ""))
        heading = replace_vars(template.get("heading", ""))
        body = replace_vars(template.get("body", ""))
        cta_text = replace_vars(template.get("cta_text", ""))
        cta_url = replace_vars(template.get("cta_url", ""))
        footer_text = replace_vars(template.get("footer_text", ""))

        # Build HTML email using the same branded layout as boutique
        html = self._build_branded_html(
            heading=heading,
            body=body,
            cta_text=cta_text,
            cta_url=cta_url,
            footer_text=footer_text,
        )

        # Build plain text version
        text = self._build_plain_text(
            heading=heading,
            body=body,
            cta_text=cta_text,
            cta_url=cta_url,
            footer_text=footer_text,
        )

        return {
            "subject": subject,
            "html": html,
            "text": text,
        }

    def _build_branded_html(
        self,
        heading: str,
        body: str,
        cta_text: str = "",
        cta_url: str = "",
        footer_text: str = "",
    ) -> str:
        """Build branded HTML email."""
        # Brand colors (matching CMS theme)
        primary_color = "#3D2817"  # Dark chocolate brown
        background_color = "#F5F5F5"
        text_color = "#333333"
        muted_color = "#666666"

        cta_html = ""
        if cta_text and cta_url:
            cta_html = f"""
            <tr>
              <td style="padding: 20px 0;">
                <table border="0" cellpadding="0" cellspacing="0">
                  <tr>
                    <td style="border-radius: 6px; background-color: {primary_color};">
                      <a href="{cta_url}" target="_blank" style="display: inline-block; padding: 14px 32px; font-size: 16px; color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: 600;">
                        {cta_text}
                      </a>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            """

        footer_html = ""
        if footer_text:
            footer_html = f"""
            <tr>
              <td style="padding: 20px 0; border-top: 1px solid #E5E5E5;">
                <p style="color: {muted_color}; font-size: 12px; margin: 0;">
                  {footer_text}
                </p>
              </td>
            </tr>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{heading}</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: {background_color};">
  <table role="presentation" style="width: 100%; border-collapse: collapse;">
    <tr>
      <td align="center" style="padding: 40px 20px;">
        <table role="presentation" style="width: 100%; max-width: 600px; border-collapse: collapse; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
          <!-- Header -->
          <tr>
            <td style="padding: 30px 40px; background-color: {primary_color}; border-radius: 8px 8px 0 0;">
              <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 600;">
                {heading}
              </h1>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding: 40px;">
              <table role="presentation" style="width: 100%; border-collapse: collapse;">
                <tr>
                  <td style="color: {text_color}; font-size: 16px; line-height: 1.6;">
                    {body}
                  </td>
                </tr>
                {cta_html}
              </table>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="padding: 20px 40px; background-color: #FAFAFA; border-radius: 0 0 8px 8px;">
              {footer_html}
              <p style="color: {muted_color}; font-size: 12px; margin: 10px 0 0 0;">
                Powered by Bakalr CMS
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    def _build_plain_text(
        self,
        heading: str,
        body: str,
        cta_text: str = "",
        cta_url: str = "",
        footer_text: str = "",
    ) -> str:
        """Build plain text version of email."""
        # Strip HTML tags from body
        clean_body = re.sub(r"<[^>]+>", "", body)
        clean_body = clean_body.replace("&nbsp;", " ")
        clean_body = re.sub(r"\s+", " ", clean_body).strip()

        lines = [
            heading,
            "=" * len(heading),
            "",
            clean_body,
            "",
        ]

        if cta_text and cta_url:
            lines.extend([f"{cta_text}: {cta_url}", ""])

        if footer_text:
            lines.extend(["---", footer_text, ""])

        lines.append("Powered by Bakalr CMS")

        return "\n".join(lines)


def get_email_template_service(db: Session, organization_id: int) -> EmailTemplateService:
    """Factory function to create EmailTemplateService."""
    return EmailTemplateService(db, organization_id)
