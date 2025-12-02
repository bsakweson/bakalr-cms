"""
SEO Management schemas and utilities
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class StructuredDataType(str, Enum):
    """Schema.org types"""

    ARTICLE = "Article"
    BLOG_POSTING = "BlogPosting"
    NEWS_ARTICLE = "NewsArticle"
    PRODUCT = "Product"
    ORGANIZATION = "Organization"
    PERSON = "Person"
    EVENT = "Event"
    RECIPE = "Recipe"
    FAQ = "FAQPage"
    HOW_TO = "HowTo"


class SEOMetadata(BaseModel):
    """Core SEO metadata"""

    title: Optional[str] = Field(None, max_length=60, description="Page title (50-60 chars)")
    description: Optional[str] = Field(
        None, max_length=160, description="Meta description (150-160 chars)"
    )
    keywords: Optional[List[str]] = Field(None, description="Keywords/tags")
    canonical_url: Optional[str] = Field(None, description="Canonical URL")
    robots: Optional[str] = Field("index,follow", description="Robots meta tag")

    @field_validator("title")
    @classmethod
    def validate_title_length(cls, v):
        if v and len(v) > 60:
            raise ValueError("SEO title should be 60 characters or less for optimal display")
        return v

    @field_validator("description")
    @classmethod
    def validate_description_length(cls, v):
        if v and len(v) > 160:
            raise ValueError("SEO description should be 160 characters or less for optimal display")
        return v


class OpenGraphMetadata(BaseModel):
    """Open Graph (Facebook) metadata"""

    og_title: Optional[str] = Field(None, description="OG title")
    og_description: Optional[str] = Field(None, description="OG description")
    og_image: Optional[str] = Field(None, description="OG image URL")
    og_image_alt: Optional[str] = Field(None, description="OG image alt text")
    og_type: Optional[str] = Field("website", description="OG type (website, article, etc.)")
    og_url: Optional[str] = Field(None, description="Canonical URL")
    og_site_name: Optional[str] = Field(None, description="Site name")
    og_locale: Optional[str] = Field("en_US", description="Locale")


class TwitterCardMetadata(BaseModel):
    """Twitter Card metadata"""

    twitter_card: Optional[str] = Field("summary_large_image", description="Card type")
    twitter_title: Optional[str] = Field(None, description="Twitter title")
    twitter_description: Optional[str] = Field(None, description="Twitter description")
    twitter_image: Optional[str] = Field(None, description="Twitter image URL")
    twitter_site: Optional[str] = Field(None, description="@username of website")
    twitter_creator: Optional[str] = Field(None, description="@username of content creator")


class StructuredData(BaseModel):
    """Schema.org structured data"""

    type: StructuredDataType = Field(..., description="Schema.org type")
    data: Dict[str, Any] = Field(..., description="Structured data properties")


class CompleteSEOData(BaseModel):
    """Complete SEO data for a content entry"""

    seo: Optional[SEOMetadata] = None
    open_graph: Optional[OpenGraphMetadata] = None
    twitter: Optional[TwitterCardMetadata] = None
    structured_data: Optional[List[StructuredData]] = None


class SEOAnalysis(BaseModel):
    """SEO analysis results"""

    score: int = Field(..., ge=0, le=100, description="SEO score (0-100)")
    issues: List[str] = Field(default_factory=list, description="SEO issues found")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")

    title_length: Optional[int] = None
    description_length: Optional[int] = None
    has_keywords: bool = False
    has_og_tags: bool = False
    has_twitter_tags: bool = False
    has_structured_data: bool = False
    has_canonical: bool = False


class SlugValidation(BaseModel):
    """Slug validation result"""

    slug: str
    is_valid: bool
    is_available: bool
    suggested_slug: Optional[str] = None
    errors: List[str] = Field(default_factory=list)


class SitemapEntry(BaseModel):
    """Single sitemap entry"""

    loc: str = Field(..., description="URL location")
    lastmod: Optional[datetime] = Field(None, description="Last modification date")
    changefreq: Optional[str] = Field("weekly", description="Change frequency")
    priority: Optional[float] = Field(0.5, ge=0.0, le=1.0, description="Priority (0.0-1.0)")


class SitemapResponse(BaseModel):
    """Sitemap response"""

    entries: List[SitemapEntry]
    total_urls: int
    generated_at: datetime


class RobotsConfig(BaseModel):
    """Robots.txt configuration"""

    user_agent: str = Field("*", description="User agent")
    allow: List[str] = Field(default_factory=list, description="Allowed paths")
    disallow: List[str] = Field(default_factory=list, description="Disallowed paths")
    crawl_delay: Optional[int] = Field(None, description="Crawl delay in seconds")
    sitemap_urls: List[str] = Field(default_factory=list, description="Sitemap URLs")


class RobotsResponse(BaseModel):
    """Robots.txt response"""

    content: str = Field(..., description="Generated robots.txt content")


class SEOUpdateRequest(BaseModel):
    """Request to update SEO metadata"""

    content_entry_id: str
    seo_data: CompleteSEOData


class CanonicalURLRequest(BaseModel):
    """Request to set canonical URL"""

    content_entry_id: str
    canonical_url: str


class BulkSEOUpdateRequest(BaseModel):
    """Bulk SEO update request"""

    content_entry_ids: List[int]
    seo_template: CompleteSEOData
