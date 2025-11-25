"""Theme model for custom theming system."""
from sqlalchemy import Column, Integer, String, Boolean, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.db.base import Base
from backend.models.base import TimestampMixin


class Theme(Base, TimestampMixin):
    """
    Theme model for storing custom themes per organization.
    
    Supports both built-in system themes and custom user-created themes.
    Each organization can have multiple themes with one active theme.
    """
    __tablename__ = "themes"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Basic theme info
    name = Column(String(100), nullable=False)  # e.g., "Dark Chocolate", "Light Mode"
    display_name = Column(String(200), nullable=False)  # User-friendly name
    description = Column(String(500))
    
    # Theme type and status
    is_system_theme = Column(Boolean, default=False, nullable=False)  # Built-in themes
    is_active = Column(Boolean, default=False, nullable=False)  # Active theme for org
    
    # Color palette (JSON)
    colors = Column(JSON, nullable=False)
    # Example structure:
    # {
    #   "primary": "#3D2817",
    #   "secondary": "#8B4513",
    #   "accent": "#D2691E",
    #   "background": "#1A1A1A",
    #   "surface": "#2D2D2D",
    #   "text": "#FFFFFF",
    #   "textSecondary": "#B0B0B0",
    #   "border": "#3D3D3D",
    #   "error": "#FF5252",
    #   "warning": "#FFC107",
    #   "success": "#4CAF50",
    #   "info": "#2196F3"
    # }
    
    # Typography settings (JSON)
    typography = Column(JSON, nullable=True)
    # Example structure:
    # {
    #   "fontFamily": "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    #   "headingFontFamily": "'Poppins', sans-serif",
    #   "fontSize": {
    #     "xs": "0.75rem",
    #     "sm": "0.875rem",
    #     "base": "1rem",
    #     "lg": "1.125rem",
    #     "xl": "1.25rem",
    #     "2xl": "1.5rem",
    #     "3xl": "1.875rem",
    #     "4xl": "2.25rem"
    #   },
    #   "fontWeight": {
    #     "normal": 400,
    #     "medium": 500,
    #     "semibold": 600,
    #     "bold": 700
    #   },
    #   "lineHeight": {
    #     "tight": 1.25,
    #     "normal": 1.5,
    #     "relaxed": 1.75
    #   }
    # }
    
    # Spacing scale (JSON)
    spacing = Column(JSON, nullable=True)
    # Example structure:
    # {
    #   "xs": "0.25rem",
    #   "sm": "0.5rem",
    #   "md": "1rem",
    #   "lg": "1.5rem",
    #   "xl": "2rem",
    #   "2xl": "3rem"
    # }
    
    # Border radius settings (JSON)
    borderRadius = Column(JSON, nullable=True)
    # Example structure:
    # {
    #   "none": "0",
    #   "sm": "0.125rem",
    #   "md": "0.375rem",
    #   "lg": "0.5rem",
    #   "xl": "0.75rem",
    #   "full": "9999px"
    # }
    
    # Shadow settings (JSON)
    shadows = Column(JSON, nullable=True)
    # Example structure:
    # {
    #   "sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
    #   "md": "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
    #   "lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1)",
    #   "xl": "0 20px 25px -5px rgba(0, 0, 0, 0.1)"
    # }
    
    # Additional custom properties (JSON) - for extensibility
    custom_properties = Column(JSON, nullable=True)
    # Can include: animations, transitions, breakpoints, etc.
    
    # Relationships
    organization = relationship("Organization", back_populates="themes")

    __table_args__ = (
        # Ensure unique theme names per organization
        Index('uix_theme_org_name', 'organization_id', 'name', unique=True),
        # Optimize lookups for active themes
        Index('ix_theme_org_active', 'organization_id', 'is_active'),
    )

    def __repr__(self):
        return f"<Theme(id={self.id}, name='{self.name}', org_id={self.organization_id}, active={self.is_active})>"
    
    def to_css_variables(self) -> dict:
        """
        Convert theme to CSS custom properties (variables).
        Returns a dictionary of CSS variable names and values.
        """
        css_vars = {}
        
        # Colors
        if self.colors:
            for key, value in self.colors.items():
                css_vars[f"--color-{key}"] = value
        
        # Typography
        if self.typography:
            if "fontFamily" in self.typography:
                css_vars["--font-family"] = self.typography["fontFamily"]
            if "headingFontFamily" in self.typography:
                css_vars["--font-family-heading"] = self.typography["headingFontFamily"]
            
            if "fontSize" in self.typography:
                for size, value in self.typography["fontSize"].items():
                    css_vars[f"--font-size-{size}"] = value
            
            if "fontWeight" in self.typography:
                for weight, value in self.typography["fontWeight"].items():
                    css_vars[f"--font-weight-{weight}"] = str(value)
        
        # Spacing
        if self.spacing:
            for key, value in self.spacing.items():
                css_vars[f"--spacing-{key}"] = value
        
        # Border radius
        if self.borderRadius:
            for key, value in self.borderRadius.items():
                css_vars[f"--radius-{key}"] = value
        
        # Shadows
        if self.shadows:
            for key, value in self.shadows.items():
                css_vars[f"--shadow-{key}"] = value
        
        return css_vars
