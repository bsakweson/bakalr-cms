"""
Pydantic schemas for content relationships.
"""
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ContentRelationshipBase(BaseModel):
    """Base schema for content relationships."""
    relationship_type: str = Field(..., description="Type of relationship (e.g., 'author', 'tags')")
    meta_data: Optional[Dict[str, Any]] = Field(None, description="Optional metadata as JSON")


class ContentRelationshipCreate(ContentRelationshipBase):
    """Schema for creating a content relationship."""
    target_entry_id: int = Field(..., description="ID of the target content entry")


class ContentRelationshipUpdate(BaseModel):
    """Schema for updating a content relationship."""
    relationship_type: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None


class ContentRelationshipResponse(ContentRelationshipBase):
    """Schema for content relationship response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    source_entry_id: int
    target_entry_id: int
    created_at: datetime
    updated_at: datetime


class RelatedContentResponse(BaseModel):
    """Schema for related content with expansion."""
    model_config = ConfigDict(from_attributes=True)
    
    relationship_id: int
    relationship_type: str
    entry_id: int
    entry_title: str
    entry_slug: str
    content_type_id: int
    meta_data: Optional[Dict[str, Any]] = None
