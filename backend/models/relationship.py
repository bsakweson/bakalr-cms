"""
Content relationship model for linking content entries.
"""
from sqlalchemy import Column, Integer, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from backend.db.base import Base
from backend.models.base import IDMixin, TimestampMixin


class ContentRelationship(Base, IDMixin, TimestampMixin):
    """
    Content Relationship model - defines relationships between content entries.
    
    Supports:
    - One-to-many (e.g., Author has many Blog Posts)
    - Many-to-one (e.g., Blog Post belongs to one Author)
    - Many-to-many (e.g., Blog Post has many Tags, Tag has many Posts)
    """
    __tablename__ = "content_relationships"
    
    # Source content entry
    source_entry_id = Column(
        Integer,
        ForeignKey("content_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Target content entry
    target_entry_id = Column(
        Integer,
        ForeignKey("content_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Relationship type/name (e.g., "author", "related_posts", "tags")
    relationship_type = Column(String(100), nullable=False, index=True)
    
    # Relationship metadata (stored as JSON)
    # Can include sort_order, custom fields, etc.
    meta_data = Column(Text, nullable=True)
    
    # Constraints: prevent duplicate relationships
    __table_args__ = (
        UniqueConstraint(
            'source_entry_id',
            'target_entry_id',
            'relationship_type',
            name='uq_content_relationship'
        ),
    )
    
    def __repr__(self):
        return (
            f"<ContentRelationship(id={self.id}, "
            f"source={self.source_entry_id}, "
            f"target={self.target_entry_id}, "
            f"type='{self.relationship_type}')>"
        )
