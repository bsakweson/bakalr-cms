"""
Avatar utilities for generating Gravatar URLs and handling avatar fallbacks.

Gravatar (Globally Recognized Avatar) is a free service that provides avatars
based on email addresses. Users can upload their avatar to gravatar.com and
any site can fetch it using an MD5 hash of their email.
"""

import hashlib
from typing import Optional
from urllib.parse import urlencode


def get_gravatar_url(
    email: str,
    size: int = 200,
    default: str = "identicon",
    rating: str = "g",
) -> str:
    """
    Generate a Gravatar URL for an email address.

    Args:
        email: The user's email address
        size: Image size in pixels (1-2048, default 200)
        default: Default image if no Gravatar exists:
            - "404": Return 404 error
            - "mp" or "mm": Mystery person silhouette
            - "identicon": Geometric pattern based on email hash
            - "monsterid": Generated monster
            - "wavatar": Generated faces
            - "retro": 8-bit arcade style
            - "robohash": Generated robot
            - "blank": Transparent PNG
        rating: Maximum rating to allow:
            - "g": General audiences
            - "pg": Parental guidance
            - "r": Restricted
            - "x": Adult only

    Returns:
        Gravatar URL for the email address
    """
    # Normalize email (lowercase, strip whitespace)
    email_normalized = email.strip().lower()

    # Generate MD5 hash of the email
    email_hash = hashlib.md5(email_normalized.encode("utf-8")).hexdigest()

    # Build query parameters
    params = {
        "s": str(size),
        "d": default,
        "r": rating,
    }

    # Construct URL
    base_url = f"https://www.gravatar.com/avatar/{email_hash}"
    return f"{base_url}?{urlencode(params)}"


def get_avatar_url(
    email: str,
    custom_avatar_url: Optional[str] = None,
    gravatar_size: int = 200,
    gravatar_default: str = "identicon",
) -> str:
    """
    Get the best available avatar URL for a user.

    Priority:
    1. Custom uploaded avatar (if provided)
    2. Gravatar (always available, with fallback to default)

    Args:
        email: The user's email address
        custom_avatar_url: URL to a custom uploaded avatar (optional)
        gravatar_size: Size for Gravatar image (default 200)
        gravatar_default: Default Gravatar style if no image exists

    Returns:
        The best available avatar URL
    """
    # If user has a custom avatar, use that
    if custom_avatar_url:
        return custom_avatar_url

    # Otherwise, fall back to Gravatar
    return get_gravatar_url(
        email=email,
        size=gravatar_size,
        default=gravatar_default,
    )


def check_gravatar_exists(email: str) -> bool:
    """
    Check if a Gravatar exists for an email address.

    This makes an HTTP request to Gravatar with d=404 to check
    if a custom avatar exists (vs. a generated fallback).

    Args:
        email: The user's email address

    Returns:
        True if a Gravatar exists, False otherwise
    """
    import httpx

    url = get_gravatar_url(email, default="404")

    try:
        response = httpx.head(url, timeout=5.0)
        return response.status_code == 200
    except httpx.RequestError:
        return False
