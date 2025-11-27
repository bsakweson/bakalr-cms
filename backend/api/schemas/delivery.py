"""
Pydantic schemas for content delivery API.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class DeliveryContentResponse(BaseModel):
    """Optimized content response for frontend delivery."""
    
    id: int
    slug: str
    title: str
    fields: Dict[str, Any] = Field(..., description="Content fields")
    published_at: Optional[datetime] = None
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class DeliveryContentListResponse(BaseModel):
    """List response for content delivery."""
    
    items: List[DeliveryContentResponse]
    total: int
    page: int
    page_size: int


class DeliveryContentDetailResponse(BaseModel):
    """Detailed content response with SEO metadata."""
    
    id: int
    slug: str
    title: str
    fields: Dict[str, Any]
    published_at: Optional[datetime]
    updated_at: datetime
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    seo_keywords: Optional[List[str]] = None
    canonical_url: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)
