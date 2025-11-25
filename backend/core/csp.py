"""
Content Security Policy (CSP) configuration for Bakalr CMS
"""
from typing import Dict, List


class CSPBuilder:
    """
    Build Content Security Policy headers
    
    Implements strict CSP to prevent XSS and data injection attacks.
    """
    
    def __init__(self):
        self.directives: Dict[str, List[str]] = {
            "default-src": ["'self'"],
            "script-src": ["'self'"],
            "style-src": ["'self'", "'unsafe-inline'"],  # unsafe-inline needed for some CSS frameworks
            "img-src": ["'self'", "data:", "https:"],
            "font-src": ["'self'", "data:"],
            "connect-src": ["'self'"],
            "media-src": ["'self'"],
            "object-src": ["'none'"],
            "frame-src": ["'none'"],
            "base-uri": ["'self'"],
            "form-action": ["'self'"],
            "frame-ancestors": ["'none'"],
            "upgrade-insecure-requests": [],
        }
    
    def add_script_src(self, *sources: str) -> "CSPBuilder":
        """Add script sources (e.g., CDN URLs)"""
        self.directives["script-src"].extend(sources)
        return self
    
    def add_style_src(self, *sources: str) -> "CSPBuilder":
        """Add style sources"""
        self.directives["style-src"].extend(sources)
        return self
    
    def add_img_src(self, *sources: str) -> "CSPBuilder":
        """Add image sources"""
        self.directives["img-src"].extend(sources)
        return self
    
    def add_connect_src(self, *sources: str) -> "CSPBuilder":
        """Add connection sources (for API calls)"""
        self.directives["connect-src"].extend(sources)
        return self
    
    def add_font_src(self, *sources: str) -> "CSPBuilder":
        """Add font sources"""
        self.directives["font-src"].extend(sources)
        return self
    
    def allow_unsafe_eval(self) -> "CSPBuilder":
        """
        Allow unsafe-eval in script-src (NOT RECOMMENDED)
        Only use if absolutely necessary for compatibility
        """
        if "'unsafe-eval'" not in self.directives["script-src"]:
            self.directives["script-src"].append("'unsafe-eval'")
        return self
    
    def build(self) -> str:
        """Build CSP header value"""
        policy_parts = []
        
        for directive, sources in self.directives.items():
            if sources:
                policy_parts.append(f"{directive} {' '.join(sources)}")
            else:
                policy_parts.append(directive)
        
        return "; ".join(policy_parts)


def get_default_csp() -> str:
    """
    Get default Content Security Policy for production
    
    Returns a strict CSP suitable for most applications.
    Customize as needed for your specific requirements.
    """
    csp = CSPBuilder()
    
    # Allow Google Fonts (commonly used)
    csp.add_font_src("https://fonts.gstatic.com")
    csp.add_style_src("https://fonts.googleapis.com")
    
    # Allow common CDNs (adjust based on your needs)
    # csp.add_script_src("https://cdn.jsdelivr.net")
    
    return csp.build()


def get_development_csp() -> str:
    """
    Get relaxed CSP for development environment
    
    More permissive to allow hot reload, dev tools, etc.
    """
    csp = CSPBuilder()
    
    # Allow unsafe-eval for dev tools
    csp.allow_unsafe_eval()
    
    # Allow localhost connections
    csp.add_connect_src("http://localhost:*", "ws://localhost:*", "https://localhost:*", "wss://localhost:*")
    
    # Allow data URIs for images
    csp.add_img_src("blob:")
    
    return csp.build()


# CORS configuration
CORS_SETTINGS = {
    "allow_origins": [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    "allow_headers": [
        "Authorization",
        "Content-Type",
        "X-CSRF-Token",
        "X-Request-ID",
        "X-API-Key",
        "X-Organization-ID",
    ],
    "expose_headers": [
        "X-Total-Count",
        "X-Page-Count",
        "X-Current-Page",
        "X-Per-Page",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "Deprecation",
        "Sunset",
        "Link",
    ],
    "max_age": 3600,  # Cache preflight requests for 1 hour
}


def get_production_cors_settings() -> dict:
    """
    Get CORS settings for production
    
    Replace with your actual production domains.
    """
    return {
        **CORS_SETTINGS,
        "allow_origins": [
            "https://yourdomain.com",
            "https://www.yourdomain.com",
            "https://admin.yourdomain.com",
        ],
    }
