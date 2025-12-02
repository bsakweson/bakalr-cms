"""Content template model for reusable content blueprints."""

import uuid

from sqlalchemy import JSON, Boolean, Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.db.base import Base
from backend.models.base import GUID, TimestampMixin


class ContentTemplate(Base, TimestampMixin):
    """
    Content Template model for storing reusable content blueprints.

    Templates define pre-configured content structures with default values,
    field mappings, and validation rules. Users can create content from templates
    to ensure consistency and speed up content creation.
    """

    __tablename__ = "content_templates"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content_type_id = Column(
        GUID(), ForeignKey("content_types.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Template info
    name = Column(String(200), nullable=False)  # e.g., "Blog Post Template", "Product Launch"
    description = Column(Text, nullable=True)

    # Template configuration
    is_system_template = Column(Boolean, default=False, nullable=False)  # Built-in templates
    is_published = Column(Boolean, default=True, nullable=False)  # Available for use

    # Icon/thumbnail for UI
    icon = Column(String(100), nullable=True)  # Icon name or emoji
    thumbnail_url = Column(String(500), nullable=True)

    # Default field values (JSON)
    # Maps field names to default values
    field_defaults = Column(JSON, nullable=False)
    # Example:
    # {
    #   "title": "New Blog Post",
    #   "author": "Admin",
    #   "status": "draft",
    #   "tags": ["news"],
    #   "featured_image": null
    # }

    # Field configuration (JSON)
    # Additional configuration per field
    field_config = Column(JSON, nullable=True)
    # Example:
    # {
    #   "title": {
    #     "required": true,
    #     "placeholder": "Enter an engaging title...",
    #     "help_text": "Keep it under 60 characters for SEO"
    #   },
    #   "content": {
    #     "required": true,
    #     "min_length": 100,
    #     "editor_mode": "rich_text"
    #   }
    # }

    # Pre-filled content structure (JSON)
    # For rich content fields like HTML/Markdown
    content_structure = Column(JSON, nullable=True)
    # Example:
    # {
    #   "content": {
    #     "type": "doc",
    #     "content": [
    #       {"type": "heading", "level": 1, "text": "Introduction"},
    #       {"type": "paragraph", "text": "Start writing here..."},
    #       {"type": "heading", "level": 2, "text": "Body"},
    #       {"type": "paragraph", "text": ""}
    #     ]
    #   }
    # }

    # Metadata and categorization
    category = Column(String(100), nullable=True)  # "blog", "product", "landing-page"
    tags = Column(JSON, nullable=True)  # ["marketing", "seasonal", "template"]

    # Usage tracking
    usage_count = Column(Integer, default=0, nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="content_templates")
    content_type = relationship("ContentType", back_populates="templates")

    __table_args__ = (
        # Ensure unique template names per organization and content type
        Index(
            "uix_template_org_type_name", "organization_id", "content_type_id", "name", unique=True
        ),
        # Optimize lookups for published templates
        Index("ix_template_published", "organization_id", "content_type_id", "is_published"),
    )

    def __repr__(self):
        return (
            f"<ContentTemplate(id={self.id}, name='{self.name}', type_id={self.content_type_id})>"
        )

    def apply_to_entry(self, entry_data: dict) -> dict:
        """
        Apply template defaults to entry data.

        Merges field_defaults with provided entry_data, with entry_data taking precedence.
        Returns the merged data ready for content entry creation.
        """
        # Start with template defaults
        merged_data = self.field_defaults.copy() if self.field_defaults else {}

        # Override with provided entry data
        if entry_data:
            merged_data.update(entry_data)

        return merged_data

    def increment_usage(self):
        """Increment the usage counter."""
        self.usage_count += 1
