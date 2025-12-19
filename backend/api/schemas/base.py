"""
Base schemas with UUID validation support
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from dateutil import parser as date_parser
from pydantic import BaseModel, field_validator


class UUIDMixin(BaseModel):
    """Mixin to automatically convert UUID and datetime fields to strings before validation"""

    @field_validator("*", mode="before")
    @classmethod
    def convert_uuids_to_str(cls, value: Any):
        """Convert UUID and datetime objects to strings, parse non-standard datetime strings"""
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        # Handle non-standard datetime strings from database (e.g., '2025-12-17 21:24:33.92821+00')
        if isinstance(value, str) and len(value) > 10:
            # Check if this looks like a datetime string that needs parsing
            if " " in value and ("+" in value or "-" in value[-6:]):
                try:
                    parsed = date_parser.parse(value)
                    return parsed.isoformat()
                except (ValueError, TypeError):
                    pass
        return value
