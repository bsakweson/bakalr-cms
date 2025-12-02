"""
Pydantic schemas for content relationships.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class ContentRelationshipBase(BaseModel):
    """Base schema for content relationships."""

    relationship_type: str = Field(..., description="Type of relationship (e.g., 'author', 'tags')")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="Optional metadata as JSON")


class ContentRelationshipCreate(ContentRelationshipBase):
    """Schema for creating a content relationship."""

    target_entry_id: str = Field(..., description="ID of the target content entry")


class ContentRelationshipUpdate(BaseModel):
    """Schema for updating a content relationship."""

    relationship_type: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None


class ContentRelationshipResponse(ContentRelationshipBase):
    """Schema for content relationship response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    source_entry_id: str
    target_entry_id: str
    created_at: datetime
    updated_at: datetime


class RelatedContentResponse(BaseModel):
    """Schema for related content with expansion."""

    model_config = ConfigDict(from_attributes=True)

    relationship_id: str
    relationship_type: str
    entry_id: str
    entry_title: str
    entry_slug: str
    content_type_id: str
    meta_data: Optional[Dict[str, Any]] = None
