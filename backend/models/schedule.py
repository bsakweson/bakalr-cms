"""
Content scheduling model for scheduled publish/unpublish actions.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.db.base import Base


class ContentSchedule(Base):
    """
    Model for scheduling content publish/unpublish actions.
    Supports timezone-aware scheduling with status tracking.
    """
    
    __tablename__ = "content_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    content_entry_id = Column(
        Integer,
        ForeignKey("content_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    action = Column(
        String(20),
        nullable=False,
        comment="Action to perform: 'publish' or 'unpublish'"
    )
    scheduled_at = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="When to execute the action"
    )
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="Status: pending, completed, failed, cancelled"
    )
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    content_entry = relationship("ContentEntry", back_populates="schedules")
    organization = relationship("Organization")
    
    def __repr__(self):
        return f"<ContentSchedule(id={self.id}, action={self.action}, scheduled_at={self.scheduled_at}, status={self.status})>"
