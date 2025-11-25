"""
Base model with common fields
"""
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.sql import func


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class IDMixin:
    """Mixin for integer primary key"""
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
