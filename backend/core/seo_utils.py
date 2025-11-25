"""
SEO utilities and helper functions
"""
import re
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from urllib.parse import quote
from backend.api.schemas.seo import (
    SEOAnalysis, 
    CompleteSEOData,
    SlugValidation,
    StructuredData,
    StructuredDataType
)


def generate_slug(text: str) -> str:
    """
    Generate URL-safe slug from text
    
    Args:
        text: Input text
        
    Returns:
        URL-safe slug
    """
    # Convert to lowercase
    slug = text.lower()
    
    # Replace spaces and special chars with hyphens
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    return slug


def validate_slug(slug: str) -> SlugValidation:
    """
    Validate slug format
    
    Args:
        slug: Slug to validate
        
    Returns:
        SlugValidation result
    """
    errors = []
    
    # Check if empty
    if not slug:
        errors.append("Slug cannot be empty")
        return SlugValidation(
            slug=slug,
            is_valid=False,
            is_available=False,
            errors=errors
        )
    
    # Check length
    if len(slug) > 200:
        errors.append("Slug too long (max 200 characters)")
    
    # Check format (lowercase, alphanumeric, hyphens only)
    if not re.match(r'^[a-z0-9-]+$', slug):
        errors.append("Slug must contain only lowercase letters, numbers, and hyphens")
    
    # Check for leading/trailing hyphens
    if slug.startswith('-') or slug.endswith('-'):
        errors.append("Slug cannot start or end with hyphen")
    
    # Check for consecutive hyphens
    if '--' in slug:
        errors.append("Slug cannot contain consecutive hyphens")
    
    # Generate suggestion if invalid
    suggested_slug = None
    if errors:
        suggested_slug = generate_slug(slug)
    
    return SlugValidation(
        slug=slug,
        is_valid=len(errors) == 0,
        is_available=False,  # Will be checked against DB
        suggested_slug=suggested_slug,
        errors=errors
    )


def analyze_seo(seo_data: Optional[CompleteSEOData]) -> SEOAnalysis:
    """
    Analyze SEO completeness and quality
    
    Args:
        seo_data: SEO metadata to analyze
        
    Returns:
        SEOAnalysis with score and suggestions
    """
    score = 0
    issues = []
    suggestions = []
    
    # Default values
    title_length = 0
    description_length = 0
    has_keywords = False
    has_og_tags = False
    has_twitter_tags = False
    has_structured_data = False
    has_canonical = False
    
    if not seo_data or not seo_data.seo:
        issues.append("No SEO metadata found")
        suggestions.append("Add basic SEO metadata (title, description)")
        return SEOAnalysis(
            score=0,
            issues=issues,
            suggestions=suggestions,
            title_length=title_length,
            description_length=description_length,
            has_keywords=has_keywords,
            has_og_tags=has_og_tags,
            has_twitter_tags=has_twitter_tags,
            has_structured_data=has_structured_data,
            has_canonical=has_canonical
        )
    
    seo = seo_data.seo
    
    # Check title
    if seo.title:
        title_length = len(seo.title)
        if 50 <= title_length <= 60:
            score += 20
        elif title_length > 60:
            issues.append("Title too long (optimal: 50-60 chars)")
            score += 10
        elif title_length < 30:
            issues.append("Title too short (optimal: 50-60 chars)")
            score += 10
        else:
            score += 15
    else:
        issues.append("Missing SEO title")
        suggestions.append("Add a descriptive title (50-60 characters)")
    
    # Check description
    if seo.description:
        description_length = len(seo.description)
        if 150 <= description_length <= 160:
            score += 20
        elif description_length > 160:
            issues.append("Description too long (optimal: 150-160 chars)")
            score += 10
        elif description_length < 120:
            issues.append("Description too short (optimal: 150-160 chars)")
            score += 10
        else:
            score += 15
    else:
        issues.append("Missing meta description")
        suggestions.append("Add a compelling description (150-160 characters)")
    
    # Check keywords
    if seo.keywords and len(seo.keywords) > 0:
        has_keywords = True
        score += 10
        if len(seo.keywords) > 10:
            issues.append("Too many keywords (recommended: 5-10)")
    else:
        suggestions.append("Add relevant keywords for better categorization")
    
    # Check canonical URL
    if seo.canonical_url:
        has_canonical = True
        score += 10
    else:
        suggestions.append("Set canonical URL to avoid duplicate content issues")
    
    # Check Open Graph
    if seo_data.open_graph:
        og = seo_data.open_graph
        if og.og_title and og.og_description and og.og_image:
            has_og_tags = True
            score += 15
        else:
            issues.append("Incomplete Open Graph metadata")
            suggestions.append("Complete Open Graph tags (title, description, image)")
    else:
        suggestions.append("Add Open Graph metadata for better social sharing")
    
    # Check Twitter Cards
    if seo_data.twitter:
        tw = seo_data.twitter
        if tw.twitter_title and tw.twitter_description and tw.twitter_image:
            has_twitter_tags = True
            score += 15
        else:
            issues.append("Incomplete Twitter Card metadata")
            suggestions.append("Complete Twitter Card tags (title, description, image)")
    else:
        suggestions.append("Add Twitter Card metadata for Twitter sharing")
    
    # Check structured data
    if seo_data.structured_data and len(seo_data.structured_data) > 0:
        has_structured_data = True
        score += 10
    else:
        suggestions.append("Add structured data (Schema.org) for rich snippets")
    
    return SEOAnalysis(
        score=min(score, 100),
        issues=issues,
        suggestions=suggestions,
        title_length=title_length,
        description_length=description_length,
        has_keywords=has_keywords,
        has_og_tags=has_og_tags,
        has_twitter_tags=has_twitter_tags,
        has_structured_data=has_structured_data,
        has_canonical=has_canonical
    )


def generate_structured_data_article(
    title: str,
    description: str,
    url: str,
    image: Optional[str] = None,
    author: Optional[str] = None,
    published_at: Optional[datetime] = None,
    modified_at: Optional[datetime] = None
) -> StructuredData:
    """
    Generate Article structured data (Schema.org)
    
    Args:
        title: Article title
        description: Article description
        url: Article URL
        image: Image URL
        author: Author name
        published_at: Publication date
        modified_at: Last modification date
        
    Returns:
        StructuredData for Article
    """
    data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "url": url
    }
    
    if image:
        data["image"] = image
    
    if author:
        data["author"] = {
            "@type": "Person",
            "name": author
        }
    
    if published_at:
        data["datePublished"] = published_at.isoformat()
    
    if modified_at:
        data["dateModified"] = modified_at.isoformat()
    
    return StructuredData(
        type=StructuredDataType.ARTICLE,
        data=data
    )


def generate_structured_data_product(
    name: str,
    description: str,
    image: Optional[str] = None,
    price: Optional[float] = None,
    currency: str = "USD",
    availability: str = "InStock",
    rating: Optional[float] = None,
    review_count: Optional[int] = None
) -> StructuredData:
    """
    Generate Product structured data (Schema.org)
    
    Args:
        name: Product name
        description: Product description
        image: Product image URL
        price: Product price
        currency: Price currency code
        availability: Stock availability
        rating: Average rating
        review_count: Number of reviews
        
    Returns:
        StructuredData for Product
    """
    data = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": name,
        "description": description
    }
    
    if image:
        data["image"] = image
    
    if price is not None:
        data["offers"] = {
            "@type": "Offer",
            "price": str(price),
            "priceCurrency": currency,
            "availability": f"https://schema.org/{availability}"
        }
    
    if rating is not None and review_count is not None:
        data["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": str(rating),
            "reviewCount": str(review_count)
        }
    
    return StructuredData(
        type=StructuredDataType.PRODUCT,
        data=data
    )


def generate_robots_txt(
    allow_paths: List[str],
    disallow_paths: List[str],
    sitemap_urls: List[str],
    crawl_delay: Optional[int] = None,
    user_agent: str = "*"
) -> str:
    """
    Generate robots.txt content
    
    Args:
        allow_paths: Allowed paths
        disallow_paths: Disallowed paths
        sitemap_urls: Sitemap URLs
        crawl_delay: Crawl delay in seconds
        user_agent: User agent
        
    Returns:
        robots.txt content
    """
    lines = [f"User-agent: {user_agent}"]
    
    # Add allowed paths
    for path in allow_paths:
        lines.append(f"Allow: {path}")
    
    # Add disallowed paths
    for path in disallow_paths:
        lines.append(f"Disallow: {path}")
    
    # Add crawl delay
    if crawl_delay is not None:
        lines.append(f"Crawl-delay: {crawl_delay}")
    
    # Add blank line before sitemaps
    if sitemap_urls:
        lines.append("")
    
    # Add sitemap URLs
    for sitemap_url in sitemap_urls:
        lines.append(f"Sitemap: {sitemap_url}")
    
    return "\n".join(lines)


def generate_sitemap_xml(entries: List[Dict[str, Any]]) -> str:
    """
    Generate XML sitemap
    
    Args:
        entries: List of sitemap entries with loc, lastmod, changefreq, priority
        
    Returns:
        XML sitemap content
    """
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    
    for entry in entries:
        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{entry['loc']}</loc>")
        
        if entry.get('lastmod'):
            lastmod = entry['lastmod']
            if isinstance(lastmod, datetime):
                lastmod = lastmod.strftime('%Y-%m-%d')
            xml_lines.append(f"    <lastmod>{lastmod}</lastmod>")
        
        if entry.get('changefreq'):
            xml_lines.append(f"    <changefreq>{entry['changefreq']}</changefreq>")
        
        if entry.get('priority'):
            xml_lines.append(f"    <priority>{entry['priority']}</priority>")
        
        xml_lines.append("  </url>")
    
    xml_lines.append("</urlset>")
    
    return "\n".join(xml_lines)
