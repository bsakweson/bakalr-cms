"""
Pydantic schemas for reference data API
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ReferenceDataItem(BaseModel):
    """Schema for a single reference data item"""

    code: str = Field(..., description="Unique code (e.g., 'SALES', 'MANAGER')")
    label: str = Field(..., description="Display label (translated if locale provided)")
    description: Optional[str] = Field(None, description="Description of the item")
    icon: Optional[str] = Field(None, description="Icon name (e.g., Lucide icon)")
    color: Optional[str] = Field(None, description="Color code in hex format")
    sort_order: int = Field(0, description="Display order")
    is_active: bool = Field(True, description="Whether the item is active")
    is_system: bool = Field(False, description="Whether this is a system default")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional properties")

    model_config = ConfigDict(from_attributes=True)


class ReferenceDataResponse(BaseModel):
    """Response for reference data list"""

    type: str = Field(..., description="Type of reference data (department, role, status, etc.)")
    locale: str = Field(..., description="Locale of the labels")
    items: List[ReferenceDataItem] = Field(..., description="List of reference data items")
    total: int = Field(..., description="Total number of items")

    model_config = ConfigDict(from_attributes=True)


class ReferenceDataTypesResponse(BaseModel):
    """Response listing available reference data types"""

    types: List[str] = Field(..., description="Available reference data types")


class ReferenceDataCreate(BaseModel):
    """Schema for creating reference data"""

    data_type: str = Field(..., description="Type of reference data")
    code: str = Field(..., pattern="^[A-Z][A-Z0-9_]*$", description="Code in UPPER_SNAKE_CASE")
    label: str = Field(..., min_length=1, max_length=255, description="Display label")
    description: Optional[str] = Field(None, description="Description")
    icon: Optional[str] = Field(None, max_length=50, description="Icon name")
    color: Optional[str] = Field(
        None, pattern="^#[0-9A-Fa-f]{6}$", description="Color in hex format"
    )
    sort_order: int = Field(0, ge=0, description="Display order")
    is_active: bool = Field(True, description="Whether active")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional properties")


class ReferenceDataUpdate(BaseModel):
    """Schema for updating reference data"""

    label: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    sort_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class ReferenceDataFullResponse(BaseModel):
    """Full response for a single reference data item"""

    id: str
    data_type: str
    code: str
    label: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: int = 0
    is_active: bool = True
    is_system: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
