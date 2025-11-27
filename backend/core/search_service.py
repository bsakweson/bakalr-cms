"""
Search service using Meilisearch for full-text search, faceting, and autocomplete.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import meilisearch
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.content import ContentEntry, ContentType


class SearchService:
    """
    Meilisearch integration for content search.
    Provides full-text search, faceted search, and autocomplete.
    """
    
    def __init__(self):
        self.client = meilisearch.Client(
            settings.MEILISEARCH_URL,
            settings.MEILISEARCH_API_KEY if settings.MEILISEARCH_API_KEY else None
        )
        self.index_name = "content_entries"
        self._ensure_index()
    
    def _ensure_index(self):
        """Create index if it doesn't exist and configure settings"""
        try:
            self.index = self.client.get_index(self.index_name)
        except Exception:
            # Index doesn't exist, create it
            task = self.client.create_index(self.index_name, {'primaryKey': 'id'})
            self.client.wait_for_task(task.task_uid)
            self.index = self.client.get_index(self.index_name)
        
        # Configure search settings
        self.index.update_settings({
            'searchableAttributes': [
                'title',
                'slug',
                'content_data',
                'content_type_name',
                'author_name',
                'tags'
            ],
            'filterableAttributes': [
                'organization_id',
                'content_type_id',
                'content_type_slug',
                'status',
                'author_id',
                'created_at_timestamp',
                'updated_at_timestamp',
                'published_at_timestamp'
            ],
            'sortableAttributes': [
                'created_at_timestamp',
                'updated_at_timestamp',
                'published_at_timestamp',
                'title'
            ],
            'displayedAttributes': [
                'id',
                'title',
                'slug',
                'content_data',
                'status',
                'content_type_id',
                'content_type_name',
                'content_type_slug',
                'author_id',
                'author_name',
                'organization_id',
                'created_at',
                'updated_at',
                'published_at'
            ],
            'typoTolerance': {
                'enabled': True,
                'minWordSizeForTypos': {
                    'oneTypo': 4,
                    'twoTypos': 8
                }
            }
        })
    
    def _content_entry_to_document(self, entry: ContentEntry, db: Session) -> Dict[str, Any]:
        """Convert ContentEntry to Meilisearch document"""
        from backend.models.user import User
        
        content_type = db.query(ContentType).filter(ContentType.id == entry.content_type_id).first()
        author = db.query(User).filter(User.id == entry.author_id).first() if entry.author_id else None
        
        # Parse JSON data
        try:
            entry_data = json.loads(entry.data) if isinstance(entry.data, str) else entry.data
        except:
            entry_data = {}
        
        # Extract text from data for better search
        content_text = ""
        if isinstance(entry_data, dict):
            for key, value in entry_data.items():
                if isinstance(value, str):
                    content_text += f" {value}"
                elif isinstance(value, (list, dict)):
                    content_text += f" {str(value)}"
        
        return {
            'id': str(entry.id),
            'title': entry.title or entry.slug,
            'slug': entry.slug,
            'content_data': content_text,
            'status': entry.status,
            'content_type_id': entry.content_type_id,
            'content_type_name': content_type.name if content_type else "",
            'content_type_slug': content_type.api_id if content_type else "",
            'author_id': entry.author_id,
            'author_name': author.email if author else "",
            'organization_id': content_type.organization_id if content_type else None,
            'tags': [],
            'created_at': entry.created_at.isoformat() if entry.created_at else None,
            'updated_at': entry.updated_at.isoformat() if entry.updated_at else None,
            'published_at': entry.published_at.isoformat() if entry.published_at else None,
            'created_at_timestamp': int(entry.created_at.timestamp()) if entry.created_at else 0,
            'updated_at_timestamp': int(entry.updated_at.timestamp()) if entry.updated_at else 0,
            'published_at_timestamp': int(entry.published_at.timestamp()) if entry.published_at else 0
        }
    
    def index_content_entry(self, entry: ContentEntry, db: Session):
        """Index a single content entry"""
        document = self._content_entry_to_document(entry, db)
        task = self.index.add_documents([document])
        return task
    
    def index_content_entries(self, entries: List[ContentEntry], db: Session):
        """Batch index multiple content entries"""
        documents = [self._content_entry_to_document(entry, db) for entry in entries]
        if documents:
            task = self.index.add_documents(documents)
            return task
        return None
    
    def delete_content_entry(self, entry_id: int):
        """Remove content entry from index"""
        task = self.index.delete_document(str(entry_id))
        return task
    
    def search(
        self,
        query: str,
        organization_id: int,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        offset: int = 0,
        sort: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Full-text search with filters and sorting.
        
        Args:
            query: Search query string
            organization_id: Organization ID for multi-tenancy
            filters: Additional filters (status, content_type_id, etc.)
            limit: Number of results to return
            offset: Number of results to skip
            sort: List of sort criteria (e.g., ['created_at_timestamp:desc'])
            
        Returns:
            Search results with hits, facets, and metadata
        """
        # Build filter string
        filter_parts = [f'organization_id = {organization_id}']
        
        if filters:
            if 'status' in filters:
                filter_parts.append(f"status = '{filters['status']}'")
            if 'content_type_id' in filters:
                filter_parts.append(f"content_type_id = {filters['content_type_id']}")
            if 'content_type_slug' in filters:
                filter_parts.append(f"content_type_slug = '{filters['content_type_slug']}'")
            if 'author_id' in filters:
                filter_parts.append(f"author_id = {filters['author_id']}")
        
        filter_str = ' AND '.join(filter_parts)
        
        # Execute search
        results = self.index.search(
            query,
            {
                'filter': filter_str,
                'limit': limit,
                'offset': offset,
                'sort': sort or ['created_at_timestamp:desc'],
                'attributesToHighlight': ['title', 'content_data'],
                'highlightPreTag': '<mark>',
                'highlightPostTag': '</mark>'
            }
        )
        
        return results
    
    def autocomplete(
        self,
        query: str,
        organization_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Autocomplete suggestions for search-as-you-type.
        
        Args:
            query: Partial search query
            organization_id: Organization ID
            limit: Number of suggestions
            
        Returns:
            List of suggestions with title and slug
        """
        results = self.index.search(
            query,
            {
                'filter': f'organization_id = {organization_id}',
                'limit': limit,
                'attributesToRetrieve': ['id', 'title', 'slug', 'content_type_name'],
                'attributesToCrop': ['title'],
                'cropLength': 50
            }
        )
        
        return results.get('hits', [])
    
    def get_facets(
        self,
        organization_id: int,
        facet_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get facet distribution for filtering.
        
        Args:
            organization_id: Organization ID
            facet_fields: List of fields to get facets for
            
        Returns:
            Facet distribution by field
        """
        if facet_fields is None:
            facet_fields = ['status', 'content_type_name', 'content_type_slug']
        
        results = self.index.search(
            '',
            {
                'filter': f'organization_id = {organization_id}',
                'facets': facet_fields,
                'limit': 0  # We only want facets, not results
            }
        )
        
        return results.get('facetDistribution', {})
    
    def reindex_all(self, db: Session, organization_id: Optional[int] = None):
        """
        Reindex all content entries (or for specific organization).
        Use for maintenance or initial setup.
        """
        query = db.query(ContentEntry)
        if organization_id:
            query = query.filter(ContentEntry.organization_id == organization_id)
        
        entries = query.all()
        return self.index_content_entries(entries, db)
    
    def clear_index(self):
        """Clear all documents from index"""
        task = self.index.delete_all_documents()
        return task


# Global search service instance
search_service = SearchService()
