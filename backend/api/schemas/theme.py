"""Pydantic schemas for theme management."""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
import re


class ColorPalette(BaseModel):
    """Color palette configuration."""
    primary: str = Field(..., description="Primary brand color")
    secondary: str = Field(..., description="Secondary brand color")
    accent: str = Field(..., description="Accent color for highlights")
    background: str = Field(..., description="Main background color")
    surface: str = Field(..., description="Surface/card background color")
    text: str = Field(..., description="Primary text color")
    textSecondary: str = Field(..., description="Secondary text color")
    border: str = Field(..., description="Border color")
    error: str = Field(..., description="Error state color")
    warning: str = Field(..., description="Warning state color")
    success: str = Field(..., description="Success state color")
    info: str = Field(..., description="Info state color")
    
    @field_validator('*')
    @classmethod
    def validate_color(cls, v: str) -> str:
        """Validate color format (hex, rgb, rgba, hsl, hsla)."""
        if not v:
            return v
        # Hex color
        if re.match(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$', v):
            return v
        # RGB/RGBA
        if re.match(r'^rgba?\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(,\s*[\d.]+\s*)?\)$', v):
            return v
        # HSL/HSLA
        if re.match(r'^hsla?\(\s*\d+\s*,\s*\d+%\s*,\s*\d+%\s*(,\s*[\d.]+\s*)?\)$', v):
            return v
        raise ValueError(f"Invalid color format: {v}. Must be hex, rgb, rgba, hsl, or hsla.")


class Typography(BaseModel):
    """Typography configuration."""
    fontFamily: Optional[str] = Field(None, description="Base font family")
    headingFontFamily: Optional[str] = Field(None, description="Heading font family")
    fontSize: Optional[Dict[str, str]] = Field(None, description="Font size scale")
    fontWeight: Optional[Dict[str, int]] = Field(None, description="Font weight scale")
    lineHeight: Optional[Dict[str, float]] = Field(None, description="Line height scale")


class Spacing(BaseModel):
    """Spacing scale configuration."""
    xs: Optional[str] = None
    sm: Optional[str] = None
    md: Optional[str] = None
    lg: Optional[str] = None
    xl: Optional[str] = None
    xl2: Optional[str] = Field(None, alias="2xl")


class BorderRadius(BaseModel):
    """Border radius configuration."""
    none: Optional[str] = None
    sm: Optional[str] = None
    md: Optional[str] = None
    lg: Optional[str] = None
    xl: Optional[str] = None
    full: Optional[str] = None


class Shadows(BaseModel):
    """Shadow configuration."""
    sm: Optional[str] = None
    md: Optional[str] = None
    lg: Optional[str] = None
    xl: Optional[str] = None


class ThemeCreate(BaseModel):
    """Schema for creating a new theme."""
    name: str = Field(..., min_length=1, max_length=100, description="Theme identifier name")
    display_name: str = Field(..., min_length=1, max_length=200, description="User-friendly display name")
    description: Optional[str] = Field(None, max_length=500, description="Theme description")
    colors: ColorPalette = Field(..., description="Color palette")
    typography: Optional[Typography] = Field(None, description="Typography settings")
    spacing: Optional[Dict[str, str]] = Field(None, description="Spacing scale")
    borderRadius: Optional[Dict[str, str]] = Field(None, description="Border radius values")
    shadows: Optional[Dict[str, str]] = Field(None, description="Shadow definitions")
    custom_properties: Optional[Dict[str, Any]] = Field(None, description="Additional custom properties")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate theme name format (lowercase, alphanumeric, hyphens, underscores)."""
        if not re.match(r'^[a-z0-9_-]+$', v):
            raise ValueError("Theme name must be lowercase alphanumeric with hyphens or underscores only")
        return v


class ThemeUpdate(BaseModel):
    """Schema for updating an existing theme."""
    display_name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    colors: Optional[ColorPalette] = None
    typography: Optional[Typography] = None
    spacing: Optional[Dict[str, str]] = None
    borderRadius: Optional[Dict[str, str]] = None
    shadows: Optional[Dict[str, str]] = None
    custom_properties: Optional[Dict[str, Any]] = None


class ThemeResponse(BaseModel):
    """Schema for theme response."""
    id: int
    organization_id: int
    name: str
    display_name: str
    description: Optional[str]
    is_system_theme: bool
    is_active: bool
    colors: Dict[str, Any]
    typography: Optional[Dict[str, Any]]
    spacing: Optional[Dict[str, Any]]
    borderRadius: Optional[Dict[str, Any]]
    shadows: Optional[Dict[str, Any]]
    custom_properties: Optional[Dict[str, Any]]
    created_at: str
    updated_at: str
    
    model_config = ConfigDict(from_attributes=True)


class ThemeListResponse(BaseModel):
    """Schema for list of themes."""
    themes: list[ThemeResponse]
    total: int
    page: int
    page_size: int


class ThemeSetActive(BaseModel):
    """Schema for setting a theme as active."""
    theme_id: int = Field(..., description="ID of the theme to set as active")


class ThemeCSSVariables(BaseModel):
    """Schema for CSS variables export."""
    theme_id: int
    theme_name: str
    css_variables: Dict[str, str] = Field(..., description="CSS custom properties")
    css_string: str = Field(..., description="CSS :root block with variables")


class ThemePreview(BaseModel):
    """Schema for theme preview with sample components."""
    theme: ThemeResponse
    preview_html: str = Field(..., description="HTML preview of theme applied to UI components")
