"""
User-Organization association model for multi-tenancy
Allows users to belong to multiple organizations with different roles in each
"""
from sqlalchemy import Column, Integer, ForeignKey, String, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship

from backend.db.base import Base
from backend.models.base import IDMixin, TimestampMixin


class UserOrganization(Base, IDMixin, TimestampMixin):
    """
    User-Organization association for multi-org support
    
    This model allows users to:
    - Belong to multiple organizations
    - Have different roles in each organization
    - Switch between organizations seamlessly
    """
    __tablename__ = "user_organizations"
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)  # Default org for this user
    
    # Role in this organization (stored as JSON array of role IDs or names)
    # This allows different roles per organization
    role_context = Column(String, nullable=True)  # JSON: ["admin", "editor"] for this org
    
    # Invitation metadata
    invited_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    invitation_accepted_at = Column(String, nullable=True)  # ISO datetime
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="user_organizations")
    organization = relationship("Organization", back_populates="user_organizations")
    inviter = relationship("User", foreign_keys=[invited_by])
    
    # Unique constraint: User can only have one membership per organization
    __table_args__ = (
        UniqueConstraint('user_id', 'organization_id', name='uq_user_organization'),
    )
    
    def __repr__(self):
        return f"<UserOrganization(user_id={self.user_id}, org_id={self.organization_id}, active={self.is_active})>"
