"""
Pydantic schemas for content scheduling system.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ScheduleContentRequest(BaseModel):
    """Request schema for scheduling content publish/unpublish."""
    
    action: str = Field(
        ...,
        pattern="^(publish|unpublish)$",
        description="Action to schedule: 'publish' or 'unpublish'"
    )
    scheduled_at: datetime = Field(
        ...,
        description="When to execute the action (timezone-aware)"
    )


class ScheduleContentResponse(BaseModel):
    """Response schema for scheduled content action."""
    
    id: int = Field(..., description="Schedule ID")
    content_entry_id: int
    action: str
    scheduled_at: datetime
    status: str = Field(
        default="pending",
        description="Status: pending, completed, failed, cancelled"
    )
    created_at: datetime
    executed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class ScheduleListResponse(BaseModel):
    """List of scheduled content actions."""
    
    items: list[ScheduleContentResponse]
    total: int
    page: int
    page_size: int
