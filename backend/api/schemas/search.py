"""
Search API schemas for requests and responses.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Schema for search request"""

    query: str = Field(..., description="Search query string", min_length=1)
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters")
    limit: int = Field(20, ge=1, le=100, description="Number of results")
    offset: int = Field(0, ge=0, description="Offset for pagination")
    sort: Optional[List[str]] = Field(None, description="Sort criteria")


class SearchHit(BaseModel):
    """Schema for a single search result"""

    id: str
    title: str
    slug: str
    content_data: Optional[str]
    status: str
    content_type_id: str
    content_type_name: str
    content_type_slug: str
    author_id: Optional[str] = None
    author_name: Optional[str] = None
    created_at: Optional[str]
    updated_at: Optional[str]
    published_at: Optional[str]
    _formatted: Optional[Dict[str, Any]] = None  # Highlighted fields


class SearchResponse(BaseModel):
    """Schema for search response"""

    hits: List[SearchHit]
    query: str
    total_hits: int
    limit: int
    offset: int
    processing_time_ms: int
    facet_distribution: Optional[Dict[str, Dict[str, int]]] = None


class AutocompleteRequest(BaseModel):
    """Schema for autocomplete request"""

    query: str = Field(..., description="Partial search query", min_length=1)
    limit: int = Field(10, ge=1, le=50, description="Number of suggestions")


class AutocompleteSuggestion(BaseModel):
    """Schema for autocomplete suggestion"""

    id: str
    title: str
    slug: str
    content_type_name: str


class AutocompleteResponse(BaseModel):
    """Schema for autocomplete response"""

    suggestions: List[AutocompleteSuggestion]
    query: str


class FacetRequest(BaseModel):
    """Schema for facet request"""

    facet_fields: Optional[List[str]] = Field(None, description="Fields to get facets for")


class FacetResponse(BaseModel):
    """Schema for facet response"""

    facets: Dict[str, Dict[str, int]]
    total_documents: int


class ReindexRequest(BaseModel):
    """Schema for reindex request"""

    organization_id: Optional[int] = Field(
        None, description="Specific organization to reindex (None for all)"
    )


class ReindexResponse(BaseModel):
    """Schema for reindex response"""

    message: str
    indexed_count: int
    task_uid: Optional[int] = None
