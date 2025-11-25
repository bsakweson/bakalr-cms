"""Default theme configurations for Bakalr CMS."""
from typing import Dict, Any


# Dark Chocolate Brown Theme (Primary brand theme)
DARK_CHOCOLATE_THEME: Dict[str, Any] = {
    "name": "dark-chocolate",
    "display_name": "Dark Chocolate",
    "description": "Rich dark chocolate brown theme with warm tones",
    "is_system_theme": True,
    "colors": {
        "primary": "#3D2817",      # Dark chocolate brown
        "secondary": "#8B4513",    # Saddle brown
        "accent": "#D2691E",       # Chocolate orange
        "background": "#1A1410",   # Very dark brown
        "surface": "#2A1F1A",      # Dark brown surface
        "text": "#F5E6D3",         # Cream text
        "textSecondary": "#C4A57B", # Light brown text
        "border": "#3D2817",       # Dark chocolate border
        "error": "#FF6B6B",        # Soft red
        "warning": "#FFA500",      # Orange
        "success": "#90EE90",      # Light green
        "info": "#87CEEB",         # Sky blue
    },
    "typography": {
        "fontFamily": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        "headingFontFamily": "'Poppins', sans-serif",
        "fontSize": {
            "xs": "0.75rem",
            "sm": "0.875rem",
            "base": "1rem",
            "lg": "1.125rem",
            "xl": "1.25rem",
            "2xl": "1.5rem",
            "3xl": "1.875rem",
            "4xl": "2.25rem",
        },
        "fontWeight": {
            "normal": 400,
            "medium": 500,
            "semibold": 600,
            "bold": 700,
        },
        "lineHeight": {
            "tight": 1.25,
            "normal": 1.5,
            "relaxed": 1.75,
        },
    },
    "spacing": {
        "xs": "0.25rem",
        "sm": "0.5rem",
        "md": "1rem",
        "lg": "1.5rem",
        "xl": "2rem",
        "2xl": "3rem",
    },
    "borderRadius": {
        "none": "0",
        "sm": "0.125rem",
        "md": "0.375rem",
        "lg": "0.5rem",
        "xl": "0.75rem",
        "full": "9999px",
    },
    "shadows": {
        "sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
        "md": "0 4px 6px -1px rgba(0, 0, 0, 0.2)",
        "lg": "0 10px 15px -3px rgba(0, 0, 0, 0.3)",
        "xl": "0 20px 25px -5px rgba(0, 0, 0, 0.4)",
    },
}

# Light Theme (Clean and professional)
LIGHT_THEME: Dict[str, Any] = {
    "name": "light",
    "display_name": "Light",
    "description": "Clean and professional light theme",
    "is_system_theme": True,
    "colors": {
        "primary": "#3D2817",      # Dark chocolate brown (brand color)
        "secondary": "#6B4423",    # Medium brown
        "accent": "#D2691E",       # Chocolate orange
        "background": "#FFFFFF",   # White
        "surface": "#F8F9FA",      # Light gray surface
        "text": "#212529",         # Dark text
        "textSecondary": "#6C757D", # Gray text
        "border": "#DEE2E6",       # Light border
        "error": "#DC3545",        # Bootstrap red
        "warning": "#FFC107",      # Bootstrap warning
        "success": "#28A745",      # Bootstrap success
        "info": "#17A2B8",         # Bootstrap info
    },
    "typography": {
        "fontFamily": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        "headingFontFamily": "'Poppins', sans-serif",
        "fontSize": {
            "xs": "0.75rem",
            "sm": "0.875rem",
            "base": "1rem",
            "lg": "1.125rem",
            "xl": "1.25rem",
            "2xl": "1.5rem",
            "3xl": "1.875rem",
            "4xl": "2.25rem",
        },
        "fontWeight": {
            "normal": 400,
            "medium": 500,
            "semibold": 600,
            "bold": 700,
        },
        "lineHeight": {
            "tight": 1.25,
            "normal": 1.5,
            "relaxed": 1.75,
        },
    },
    "spacing": {
        "xs": "0.25rem",
        "sm": "0.5rem",
        "md": "1rem",
        "lg": "1.5rem",
        "xl": "2rem",
        "2xl": "3rem",
    },
    "borderRadius": {
        "none": "0",
        "sm": "0.125rem",
        "md": "0.375rem",
        "lg": "0.5rem",
        "xl": "0.75rem",
        "full": "9999px",
    },
    "shadows": {
        "sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
        "md": "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
        "lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1)",
        "xl": "0 20px 25px -5px rgba(0, 0, 0, 0.1)",
    },
}

# Dark Theme (Modern dark mode)
DARK_THEME: Dict[str, Any] = {
    "name": "dark",
    "display_name": "Dark",
    "description": "Modern dark theme with high contrast",
    "is_system_theme": True,
    "colors": {
        "primary": "#D2691E",      # Chocolate orange (lighter for dark mode)
        "secondary": "#8B4513",    # Saddle brown
        "accent": "#FF8C42",       # Bright orange
        "background": "#0D1117",   # GitHub dark background
        "surface": "#161B22",      # GitHub dark surface
        "text": "#C9D1D9",         # GitHub dark text
        "textSecondary": "#8B949E", # GitHub dark secondary text
        "border": "#30363D",       # GitHub dark border
        "error": "#F85149",        # GitHub dark red
        "warning": "#D29922",      # GitHub dark yellow
        "success": "#3FB950",      # GitHub dark green
        "info": "#58A6FF",         # GitHub dark blue
    },
    "typography": {
        "fontFamily": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        "headingFontFamily": "'Poppins', sans-serif",
        "fontSize": {
            "xs": "0.75rem",
            "sm": "0.875rem",
            "base": "1rem",
            "lg": "1.125rem",
            "xl": "1.25rem",
            "2xl": "1.5rem",
            "3xl": "1.875rem",
            "4xl": "2.25rem",
        },
        "fontWeight": {
            "normal": 400,
            "medium": 500,
            "semibold": 600,
            "bold": 700,
        },
        "lineHeight": {
            "tight": 1.25,
            "normal": 1.5,
            "relaxed": 1.75,
        },
    },
    "spacing": {
        "xs": "0.25rem",
        "sm": "0.5rem",
        "md": "1rem",
        "lg": "1.5rem",
        "xl": "2rem",
        "2xl": "3rem",
    },
    "borderRadius": {
        "none": "0",
        "sm": "0.125rem",
        "md": "0.375rem",
        "lg": "0.5rem",
        "xl": "0.75rem",
        "full": "9999px",
    },
    "shadows": {
        "sm": "0 1px 2px 0 rgba(0, 0, 0, 0.3)",
        "md": "0 4px 6px -1px rgba(0, 0, 0, 0.4)",
        "lg": "0 10px 15px -3px rgba(0, 0, 0, 0.5)",
        "xl": "0 20px 25px -5px rgba(0, 0, 0, 0.6)",
    },
}

# All default themes
DEFAULT_THEMES = [
    DARK_CHOCOLATE_THEME,
    LIGHT_THEME,
    DARK_THEME,
]


def get_default_theme_by_name(name: str) -> Dict[str, Any] | None:
    """Get a default theme by name."""
    for theme in DEFAULT_THEMES:
        if theme["name"] == name:
            return theme
    return None


def get_default_active_theme() -> Dict[str, Any]:
    """Get the default active theme (Dark Chocolate)."""
    return DARK_CHOCOLATE_THEME
