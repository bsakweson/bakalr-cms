"""
Base schemas with UUID validation support
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, field_validator


class UUIDMixin(BaseModel):
    """Mixin to automatically convert UUID and datetime fields to strings before validation"""

    @field_validator("*", mode="before")
    @classmethod
    def convert_uuids_to_str(cls, value: Any):
        """Convert UUID and datetime objects to strings"""
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        return value
