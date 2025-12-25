"""
Content Type model for dynamic content schemas
"""

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.db.base import Base
from backend.models.base import GUID, IDMixin, TimestampMixin


class ContentType(Base, IDMixin, TimestampMixin):
    """
    Content Type model - defines the structure of content (like Contentful)
    Each organization can create custom content types with dynamic fields
    """

    __tablename__ = "content_types"

    # Organization (Tenant)
    organization_id = Column(
        GUID, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Content Type Info
    name = Column(String(255), nullable=False)  # Display name (e.g., "Blog Post")
    api_id = Column(String(100), nullable=False, index=True)  # API identifier (e.g., "blog_post")
    description = Column(Text, nullable=True)

    # Icon for UI
    icon = Column(String(100), nullable=True)

    # Field schema (stored as JSON)
    # Example: [{"name": "title", "type": "text", "required": true}, ...]
    fields_schema = Column(Text, nullable=False)  # JSON string

    # Settings
    is_published = Column(Boolean, default=True, nullable=False)
    allow_comments = Column(Boolean, default=False, nullable=False)

    # Display settings (stored as JSON)
    display_settings = Column(Text, nullable=True)  # JSON string

    # Relationships
    organization = relationship("Organization", back_populates="content_types")
    entries = relationship(
        "ContentEntry", back_populates="content_type", cascade="all, delete-orphan"
    )
    templates = relationship(
        "ContentTemplate", back_populates="content_type", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<ContentType(id={self.id}, name='{self.name}', api_id='{self.api_id}')>"


class ContentEntry(Base, IDMixin, TimestampMixin):
    """
    Content Entry model - actual content instances of a content type
    """

    __tablename__ = "content_entries"

    # Content Type
    content_type_id = Column(
        GUID, ForeignKey("content_types.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Entry Info
    title = Column(String(500), nullable=False)
    slug = Column(String(255), nullable=False, index=True)

    # Content data (stored as JSON matching the content type schema)
    data = Column(Text, nullable=False)  # JSON string

    # Publishing
    status = Column(
        String(20), default="draft", nullable=False, index=True
    )  # draft, published, archived
    published_at = Column(String, nullable=True)  # ISO datetime string

    # Author (User who created this)
    author_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Versioning
    version = Column(Integer, default=1, nullable=False)

    # SEO
    seo_data = Column(Text, nullable=True)  # JSON string with meta_title, meta_description, etc.

    # Relationships
    content_type = relationship("ContentType", back_populates="entries")
    author = relationship("User", foreign_keys=[author_id], backref="authored_entries")
    translations = relationship(
        "Translation", back_populates="content_entry", cascade="all, delete-orphan"
    )
    schedules = relationship(
        "ContentSchedule", back_populates="content_entry", cascade="all, delete-orphan"
    )

    # Content relationships (outgoing)
    outgoing_relationships = relationship(
        "ContentRelationship",
        foreign_keys="ContentRelationship.source_entry_id",
        cascade="all, delete-orphan",
        backref="source_entry",
    )

    # Content relationships (incoming)
    incoming_relationships = relationship(
        "ContentRelationship",
        foreign_keys="ContentRelationship.target_entry_id",
        cascade="all, delete-orphan",
        backref="target_entry",
    )

    def __repr__(self):
        return f"<ContentEntry(id={self.id}, title='{self.title}', status='{self.status}')>"
