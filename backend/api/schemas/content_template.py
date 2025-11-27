"""Pydantic schemas for content templates."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class FieldConfig(BaseModel):
    """Configuration for a single field in a template."""

    required: Optional[bool] = None
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    editor_mode: Optional[str] = None  # "plain_text", "rich_text", "markdown"
    validation_pattern: Optional[str] = None


class ContentTemplateCreate(BaseModel):
    """Schema for creating a content template."""

    content_type_id: int = Field(..., description="ID of the content type this template is for")
    name: str = Field(..., min_length=1, max_length=200, description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    icon: Optional[str] = Field(None, max_length=100, description="Icon name or emoji")
    thumbnail_url: Optional[str] = Field(None, max_length=500, description="Thumbnail image URL")
    field_defaults: Dict[str, Any] = Field(..., description="Default values for fields")
    field_config: Optional[Dict[str, FieldConfig]] = Field(None, description="Field configuration")
    content_structure: Optional[Dict[str, Any]] = Field(
        None, description="Pre-filled content structure"
    )
    category: Optional[str] = Field(None, max_length=100, description="Template category")
    tags: Optional[List[str]] = Field(None, description="Template tags")
    is_published: bool = Field(True, description="Whether template is available for use")


class ContentTemplateUpdate(BaseModel):
    """Schema for updating a content template."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=100)
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    field_defaults: Optional[Dict[str, Any]] = None
    field_config: Optional[Dict[str, FieldConfig]] = None
    content_structure: Optional[Dict[str, Any]] = None
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = None
    is_published: Optional[bool] = None


class ContentTemplateResponse(BaseModel):
    """Schema for content template response."""

    id: int
    organization_id: int
    content_type_id: int
    name: str
    description: Optional[str]
    is_system_template: bool
    is_published: bool
    icon: Optional[str]
    thumbnail_url: Optional[str]
    field_defaults: Dict[str, Any]
    field_config: Optional[Dict[str, Any]]
    content_structure: Optional[Dict[str, Any]]
    category: Optional[str]
    tags: Optional[List[str]]
    usage_count: int
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class ContentTemplateListResponse(BaseModel):
    """Schema for list of templates."""

    templates: List[ContentTemplateResponse]
    total: int
    page: int
    page_size: int


class ContentTemplateApply(BaseModel):
    """Schema for applying a template to create content."""

    template_id: int = Field(..., description="ID of template to apply")
    overrides: Optional[Dict[str, Any]] = Field(
        None, description="Field values to override template defaults"
    )
    title: Optional[str] = Field(None, description="Content entry title")
    slug: Optional[str] = Field(None, description="Content entry slug")


class ContentTemplateApplyResponse(BaseModel):
    """Response after applying a template."""

    content_entry_id: int
    template_id: int
    template_name: str
    applied_data: Dict[str, Any]
    message: str


class TemplateStats(BaseModel):
    """Template usage statistics."""

    template_id: int
    template_name: str
    usage_count: int
    last_used: Optional[str]
    total_content_created: int
