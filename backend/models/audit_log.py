"""
Audit Log model for tracking all changes
"""
from sqlalchemy import Column, String, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship

from backend.db.base import Base
from backend.models.base import IDMixin, TimestampMixin


class AuditLog(Base, IDMixin, TimestampMixin):
    """
    Audit Log model - tracks all user actions for security and compliance
    """
    __tablename__ = "audit_logs"

    # Organization (Tenant)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # User who performed the action
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Action Info
    action = Column(String(100), nullable=False, index=True)  # create, update, delete, login, etc.
    resource_type = Column(String(100), nullable=False, index=True)  # user, content, role, etc.
    resource_id = Column(Integer, nullable=True, index=True)
    
    # Details
    description = Column(Text, nullable=True)
    
    # Changes (before/after snapshots - stored as JSON)
    changes = Column(Text, nullable=True)  # JSON object: {before: {...}, after: {...}}
    
    # Request metadata
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)
    
    # Severity
    severity = Column(String(20), default="info", nullable=False)  # info, warning, error, critical
    
    # Status
    status = Column(String(20), default="success", nullable=False)  # success, failure
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', resource='{self.resource_type}')>"
