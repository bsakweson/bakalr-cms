"""
Search API endpoints for full-text search, autocomplete, and faceting.
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, status, Request
from sqlalchemy.orm import Session

from backend.api.schemas.search import (
    SearchRequest, SearchResponse, SearchHit,
    AutocompleteRequest, AutocompleteResponse, AutocompleteSuggestion,
    FacetRequest, FacetResponse,
    ReindexRequest, ReindexResponse
)
from backend.core.dependencies import get_db, get_current_user
from backend.core.permissions import PermissionChecker
from backend.core.search_service import search_service
from backend.models.user import User
from backend.models.content import ContentEntry
from backend.core.rate_limit import limiter, get_rate_limit
from backend.core.config import settings


router = APIRouter(prefix="/search", tags=["Search"])


@router.post("", response_model=SearchResponse)
@limiter.limit(get_rate_limit())
async def search_content(
    request: Request,
    search_request: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Full-text search across all content entries.
    Supports filtering, sorting, and highlighting.
    """
    results = search_service.search(
        query=search_request.query,
        organization_id=current_user.organization_id,
        filters=search_request.filters,
        limit=search_request.limit,
        offset=search_request.offset,
        sort=search_request.sort
    )
    
    # Convert hits to response model
    hits = []
    for hit in results.get('hits', []):
        hits.append(SearchHit(**hit))
    
    return SearchResponse(
        hits=hits,
        query=results.get('query', search_request.query),
        total_hits=results.get('estimatedTotalHits', 0),
        limit=results.get('limit', search_request.limit),
        offset=results.get('offset', search_request.offset),
        processing_time_ms=results.get('processingTimeMs', 0),
        facet_distribution=results.get('facetDistribution')
    )


@router.get("", response_model=SearchResponse)
@limiter.limit(get_rate_limit())
async def search_content_get(
    request: Request,
    query: str = Query(..., description="Search query", min_length=1),
    status: Optional[str] = Query(None, description="Filter by status"),
    content_type_slug: Optional[str] = Query(None, description="Filter by content type"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    sort_by: Optional[str] = Query(None, description="Sort by field (created_at, updated_at, published_at)"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc, desc)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Full-text search with query parameters (GET endpoint).
    Alternative to POST endpoint for simple searches.
    """
    filters = {}
    if status:
        filters['status'] = status
    if content_type_slug:
        filters['content_type_slug'] = content_type_slug
    
    sort = None
    if sort_by:
        sort_field = f"{sort_by}_timestamp" if sort_by in ['created_at', 'updated_at', 'published_at'] else sort_by
        sort = [f"{sort_field}:{sort_order}"]
    
    results = search_service.search(
        query=query,
        organization_id=current_user.organization_id,
        filters=filters,
        limit=limit,
        offset=offset,
        sort=sort
    )
    
    hits = [SearchHit(**hit) for hit in results.get('hits', [])]
    
    return SearchResponse(
        hits=hits,
        query=results.get('query', query),
        total_hits=results.get('estimatedTotalHits', 0),
        limit=results.get('limit', limit),
        offset=results.get('offset', offset),
        processing_time_ms=results.get('processingTimeMs', 0),
        facet_distribution=results.get('facetDistribution')
    )


@router.post("/autocomplete", response_model=AutocompleteResponse)
@limiter.limit(get_rate_limit())
async def autocomplete_search(
    request: Request,
    autocomplete_request: AutocompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Autocomplete suggestions for search-as-you-type.
    Returns top matching content entries.
    """
    suggestions = search_service.autocomplete(
        query=autocomplete_request.query,
        organization_id=current_user.organization_id,
        limit=autocomplete_request.limit
    )
    
    # Convert to response model
    suggestion_list = [
        AutocompleteSuggestion(
            id=s['id'],
            title=s.get('title', ''),
            slug=s.get('slug', ''),
            content_type_name=s.get('content_type_name', '')
        )
        for s in suggestions
    ]
    
    return AutocompleteResponse(
        suggestions=suggestion_list,
        query=autocomplete_request.query
    )


@router.get("/autocomplete", response_model=AutocompleteResponse)
@limiter.limit(get_rate_limit())
async def autocomplete_search_get(
    request: Request,
    query: str = Query(..., description="Partial search query", min_length=1),
    limit: int = Query(10, ge=1, le=50, description="Number of suggestions"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Autocomplete suggestions (GET endpoint).
    Alternative to POST endpoint for simple autocomplete.
    """
    suggestions = search_service.autocomplete(
        query=query,
        organization_id=current_user.organization_id,
        limit=limit
    )
    
    suggestion_list = [
        AutocompleteSuggestion(
            id=s['id'],
            title=s.get('title', ''),
            slug=s.get('slug', ''),
            content_type_name=s.get('content_type_name', '')
        )
        for s in suggestions
    ]
    
    return AutocompleteResponse(
        suggestions=suggestion_list,
        query=query
    )


@router.post("/facets", response_model=FacetResponse)
@limiter.limit(get_rate_limit())
async def get_facets(
    request: Request,
    facet_request: FacetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get facet distribution for filtering.
    Returns counts for each facet value (status, content type, etc.).
    """
    facets = search_service.get_facets(
        organization_id=current_user.organization_id,
        facet_fields=facet_request.facet_fields
    )
    
    # Get total document count
    stats_result = search_service.index.get_stats()
    total_documents = stats_result.get('numberOfDocuments', 0)
    
    return FacetResponse(
        facets=facets,
        total_documents=total_documents
    )


@router.get("/facets", response_model=FacetResponse)
@limiter.limit(get_rate_limit())
async def get_facets_get(
    request: Request,
    fields: Optional[str] = Query(None, description="Comma-separated facet fields"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get facet distribution (GET endpoint).
    Alternative to POST endpoint for simple facet requests.
    """
    facet_fields = fields.split(',') if fields else None
    
    facets = search_service.get_facets(
        organization_id=current_user.organization_id,
        facet_fields=facet_fields
    )
    
    stats_result = search_service.index.get_stats()
    total_documents = stats_result.get('numberOfDocuments', 0)
    
    return FacetResponse(
        facets=facets,
        total_documents=total_documents
    )


@router.post("/reindex", response_model=ReindexResponse)
@limiter.limit(get_rate_limit())
async def reindex_content(
    request: Request,
    reindex_request: ReindexRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reindex all content entries for current organization.
    Requires admin permissions.
    """
    PermissionChecker.require_permission(current_user, "content.manage", db)
    
    # Count entries to be indexed
    query = db.query(ContentEntry).filter(
        ContentEntry.organization_id == current_user.organization_id
    )
    
    if reindex_request.organization_id:
        # Verify user has access to specified organization
        if reindex_request.organization_id != current_user.organization_id:
            PermissionChecker.require_permission(current_user, "system.admin", db)
        query = query.filter(ContentEntry.organization_id == reindex_request.organization_id)
    
    entries = query.all()
    indexed_count = len(entries)
    
    # Reindex
    task = search_service.index_content_entries(entries, db)
    
    return ReindexResponse(
        message=f"Reindexing {indexed_count} content entries",
        indexed_count=indexed_count,
        task_uid=task.task_uid if task else None
    )


@router.delete("/index", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(get_rate_limit())
async def clear_search_index(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Clear the entire search index.
    Requires system admin permissions. Use with caution!
    """
    PermissionChecker.require_permission(current_user, "system.admin", db)
    
    search_service.clear_index()
    
    return None
