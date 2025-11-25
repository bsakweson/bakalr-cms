"""
Input sanitization and XSS protection utilities.
"""
import re
import html
from typing import Any, Dict, List, Union


class Sanitizer:
    """Input sanitization utilities."""
    
    # HTML tags to allow in rich text (whitelist)
    ALLOWED_TAGS = {
        'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'a', 'img', 'blockquote', 'code', 'pre',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
    }
    
    # HTML attributes to allow (whitelist)
    ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title', 'target'],
        'img': ['src', 'alt', 'title', 'width', 'height'],
        'table': ['border', 'cellpadding', 'cellspacing'],
    }
    
    # Dangerous patterns to block
    DANGEROUS_PATTERNS = [
        r'javascript:',
        r'on\w+\s*=',  # Event handlers (onclick, onerror, etc.)
        r'<script',
        r'</script>',
        r'<iframe',
        r'</iframe>',
        r'<object',
        r'</object>',
        r'<embed',
        r'</embed>',
    ]
    
    @classmethod
    def sanitize_string(cls, text: str, allow_html: bool = False) -> str:
        """
        Sanitize a string input.
        
        Args:
            text: Input text to sanitize
            allow_html: If True, allow safe HTML tags (for rich text fields)
        
        Returns:
            Sanitized string
        """
        if not text:
            return text
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        if not allow_html:
            # Escape all HTML
            return html.escape(text)
        
        # For rich text, remove dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Basic tag stripping (keep only allowed tags)
        # This is a simple implementation; for production use bleach or html5lib
        return text
    
    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any], rich_text_fields: List[str] = None) -> Dict[str, Any]:
        """
        Recursively sanitize dictionary values.
        
        Args:
            data: Dictionary to sanitize
            rich_text_fields: List of field names that allow HTML
        
        Returns:
            Sanitized dictionary
        """
        if rich_text_fields is None:
            rich_text_fields = []
        
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                allow_html = key in rich_text_fields
                sanitized[key] = cls.sanitize_string(value, allow_html=allow_html)
            elif isinstance(value, dict):
                sanitized[key] = cls.sanitize_dict(value, rich_text_fields)
            elif isinstance(value, list):
                sanitized[key] = [
                    cls.sanitize_dict(item, rich_text_fields) if isinstance(item, dict)
                    else cls.sanitize_string(item, allow_html=False) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized
    
    @classmethod
    def validate_slug(cls, slug: str) -> bool:
        """
        Validate URL slug format.
        
        Args:
            slug: URL slug to validate
        
        Returns:
            True if valid, False otherwise
        """
        # Allow lowercase letters, numbers, hyphens
        pattern = r'^[a-z0-9]+(?:-[a-z0-9]+)*$'
        return bool(re.match(pattern, slug))
    
    @classmethod
    def validate_email(cls, email: str) -> bool:
        """
        Validate email format.
        
        Args:
            email: Email address to validate
        
        Returns:
            True if valid, False otherwise
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @classmethod
    def validate_url(cls, url: str, allow_relative: bool = False) -> bool:
        """
        Validate URL format.
        
        Args:
            url: URL to validate
            allow_relative: If True, allow relative URLs
        
        Returns:
            True if valid, False otherwise
        """
        if allow_relative and url.startswith('/'):
            return True
        
        # Basic URL validation (http/https)
        pattern = r'^https?://[a-zA-Z0-9.-]+(?:\.[a-zA-Z]{2,})+(?:/[^\s]*)?$'
        return bool(re.match(pattern, url))
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """
        Sanitize filename to prevent directory traversal.
        
        Args:
            filename: Original filename
        
        Returns:
            Sanitized filename
        """
        # Remove path separators and null bytes
        filename = filename.replace('/', '').replace('\\', '').replace('\x00', '')
        
        # Remove leading dots to prevent hidden files
        filename = filename.lstrip('.')
        
        # Replace spaces with underscores
        filename = filename.replace(' ', '_')
        
        # Remove any remaining dangerous characters
        filename = re.sub(r'[^\w\-\.]', '', filename)
        
        return filename or 'unnamed'


def sanitize_input(data: Union[str, Dict, List], **kwargs) -> Union[str, Dict, List]:
    """
    Convenience function to sanitize various input types.
    
    Args:
        data: Data to sanitize (string, dict, or list)
        **kwargs: Additional arguments for Sanitizer methods
    
    Returns:
        Sanitized data
    """
    if isinstance(data, str):
        return Sanitizer.sanitize_string(data, **kwargs)
    elif isinstance(data, dict):
        return Sanitizer.sanitize_dict(data, **kwargs)
    elif isinstance(data, list):
        return [sanitize_input(item, **kwargs) for item in data]
    return data
