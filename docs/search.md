# Search & Discovery Guide

Full-text search capabilities with Meilisearch integration.

## Table of Contents

- [Overview](#overview)
- [Setup & Configuration](#setup--configuration)
- [Search API](#search-api)
- [Advanced Features](#advanced-features)
- [Search Analytics](#search-analytics)
- [Best Practices](#best-practices)

## Overview

Bakalr CMS provides powerful full-text search capabilities powered by [Meilisearch](https://www.meilisearch.com/), an open-source search engine optimized for speed and relevance.

### Key Features

✨ **Typo Tolerance**: Automatically handles typos and spelling mistakes  
🔍 **Fuzzy Matching**: Finds relevant results even with approximate queries  
⚡ **Instant Results**: Sub-50ms search response times  
🎯 **Relevance Ranking**: Smart ranking based on content and context  
🌈 **Highlighting**: Highlights search terms in results  
📊 **Faceted Search**: Filter by content type, status, dates, and custom fields  
🔤 **Autocomplete**: Real-time search suggestions  
🌍 **Multi-language**: Search across all your content locales  

### When to Use Search vs Filtering

**Use Meilisearch Search When:**
- Users are performing text queries ("find blog posts about APIs")
- You need typo tolerance and fuzzy matching
- Speed is critical (<50ms response times)
- You want relevance-based ranking

**Use Database Filtering When:**
- Exact field matching is required
- Filtering by specific IDs, dates, or statuses
- Simple queries with known values
- Complex relational queries

## Setup & Configuration

### Installation

#### Option 1: Docker Compose (Recommended)

Meilisearch is included in the default `docker-compose.yml`:

```bash
# Start all services including Meilisearch
docker-compose up -d

# Meilisearch is available at http://localhost:7700
```

#### Option 2: Local Installation

**macOS (Homebrew)**:
```bash
brew install meilisearch
brew services start meilisearch
```

**Linux**:
```bash
# Download and install
curl -L https://install.meilisearch.com | sh

# Run Meilisearch
./meilisearch
```

**Windows**:
```powershell
# Download from https://github.com/meilisearch/meilisearch/releases
# Run the executable
meilisearch.exe
```

### Configuration

Configure Meilisearch in your `.env` file:

```bash
# Meilisearch Configuration
MEILISEARCH_URL=http://localhost:7700
MEILISEARCH_API_KEY=your-master-key-here  # Optional for development

# Search Rate Limiting
RATE_LIMIT_SEARCH=500/hour;50/minute
```

**Production Settings**:

```bash
# Use environment variables for security
MEILISEARCH_URL=https://search.yourdomain.com
MEILISEARCH_API_KEY=${MEILISEARCH_MASTER_KEY}  # From secrets
MEILISEARCH_INDEX_PREFIX=bakalr_cms_  # Optional prefix for multi-tenant
```

### Index Configuration

Bakalr CMS automatically creates and manages Meilisearch indexes for your content.

**Index Naming**:
- Content entries: `content_entries`
- By organization: `content_entries_org_{organization_id}`

**Indexed Fields**:
- `id` - Content entry ID
- `title` - Entry title
- `slug` - URL slug
- `content_data` - Full content body
- `status` - Publication status
- `content_type_id` - Type of content
- `content_type_name` - Type name (e.g., "blog_post")
- `author_id` - Author user ID
- `organization_id` - Organization/tenant ID
- `published_at` - Publication timestamp
- `created_at` - Creation timestamp

### Reindexing Content

To reindex all content (updates Meilisearch with latest data):

**API Endpoint**:
```bash
POST /api/v1/search/reindex
Authorization: Bearer {your_token}
```

**Example**:
```bash
curl -X POST http://localhost:8000/api/v1/search/reindex \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response**:
```json
{
  "message": "Reindexing started",
  "total_entries": 1523,
  "indexes": ["content_entries"]
}
```

**When to Reindex**:
- After restoring from database backup
- After bulk content imports
- If search results seem out of sync
- After Meilisearch version upgrades

## Search API

### Basic Search

**Endpoint**: `GET /api/v1/search`

**Parameters**:
- `q` (required): Search query string
- `limit` (optional): Number of results (default: 20, max: 100)
- `offset` (optional): Pagination offset (default: 0)
- `content_types` (optional): Filter by content type slugs (comma-separated)
- `status` (optional): Filter by status (draft, published, archived)

**Example - Simple Search**:
```bash
curl -X GET "http://localhost:8000/api/v1/search?q=python tutorial" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response**:
```json
{
  "hits": [
    {
      "id": 42,
      "title": "Getting Started with Python",
      "slug": "python-tutorial",
      "content_data": {
        "body": "Learn Python programming...",
        "excerpt": "A comprehensive guide..."
      },
      "content_type_name": "blog_post",
      "status": "published",
      "published_at": "2025-11-20T10:00:00Z",
      "_formatted": {
        "title": "Getting Started with <em>Python</em>",
        "body": "Learn <em>Python</em> programming..."
      }
    }
  ],
  "total": 15,
  "limit": 20,
  "offset": 0,
  "processing_time_ms": 12,
  "query": "python tutorial"
}
```

### Filter by Content Type

Search within specific content types:

```bash
# Search only blog posts
curl -X GET "http://localhost:8000/api/v1/search?q=API&content_types=blog_post" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Search multiple content types
curl -X GET "http://localhost:8000/api/v1/search?q=API&content_types=blog_post,documentation" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Filter by Status

Search only published content:

```bash
curl -X GET "http://localhost:8000/api/v1/search?q=tutorial&status=published" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Pagination

Navigate through large result sets:

```bash
# First page (20 results)
curl -X GET "http://localhost:8000/api/v1/search?q=tutorial&limit=20&offset=0" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Second page
curl -X GET "http://localhost:8000/api/v1/search?q=tutorial&limit=20&offset=20" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Third page
curl -X GET "http://localhost:8000/api/v1/search?q=tutorial&limit=20&offset=40" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Python SDK Example

```python
from bakalr_sdk import BakalrClient

client = BakalrClient(
    api_url="http://localhost:8000",
    api_key="your-api-key"
)

# Simple search
results = client.search.query(
    q="Python tutorial",
    limit=10
)

print(f"Found {results['total']} results")
for hit in results['hits']:
    print(f"- {hit['title']} ({hit['content_type_name']})")

# Filtered search
blog_posts = client.search.query(
    q="API",
    content_types=["blog_post"],
    status="published",
    limit=20
)
```

### JavaScript/TypeScript Example

```typescript
import { BakalrClient } from '@bakalr/sdk';

const client = new BakalrClient({
  apiUrl: 'http://localhost:8000',
  apiKey: 'your-api-key'
});

// Simple search
const results = await client.search.query({
  q: 'Python tutorial',
  limit: 10
});

console.log(`Found ${results.total} results`);
results.hits.forEach(hit => {
  console.log(`- ${hit.title} (${hit.content_type_name})`);
});

// Filtered search
const blogPosts = await client.search.query({
  q: 'API',
  contentTypes: ['blog_post'],
  status: 'published',
  limit: 20
});
```

## Advanced Features

### Typo Tolerance

Meilisearch automatically handles typos and spelling mistakes:

```bash
# Query with typo: "phyton" instead of "python"
curl -X GET "http://localhost:8000/api/v1/search?q=phyton tutrial" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Still finds "Python tutorial" results
```

**Typo Rules**:
- 1-4 characters: No typos allowed
- 5-8 characters: 1 typo allowed
- 9+ characters: 2 typos allowed

### Highlighting

Search terms are automatically highlighted in results with `<em>` tags:

```json
{
  "hits": [
    {
      "title": "Python Tutorial",
      "_formatted": {
        "title": "<em>Python</em> Tutorial",
        "body": "Learn <em>Python</em> programming with this guide"
      }
    }
  ]
}
```

**Frontend Usage**:
```jsx
// React component
function SearchResult({ hit }) {
  return (
    <div>
      <h3 dangerouslySetInnerHTML={{ __html: hit._formatted.title }} />
      <p dangerouslySetInnerHTML={{ __html: hit._formatted.body }} />
    </div>
  );
}
```

### Autocomplete

Get search suggestions as users type:

**Endpoint**: `GET /api/v1/search/autocomplete`

```bash
curl -X GET "http://localhost:8000/api/v1/search/autocomplete?q=pyth" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response**:
```json
{
  "suggestions": [
    "python",
    "python tutorial",
    "python api",
    "python best practices"
  ],
  "limit": 10
}
```

**Frontend Implementation**:
```jsx
import { useState, useEffect } from 'react';
import { debounce } from 'lodash';

function SearchBox() {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);

  const fetchSuggestions = debounce(async (q) => {
    if (q.length < 2) return;
    
    const response = await fetch(
      `http://localhost:8000/api/v1/search/autocomplete?q=${q}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    const data = await response.json();
    setSuggestions(data.suggestions);
  }, 300);

  useEffect(() => {
    fetchSuggestions(query);
  }, [query]);

  return (
    <div>
      <input
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search..."
      />
      {suggestions.length > 0 && (
        <ul className="suggestions">
          {suggestions.map((s, i) => (
            <li key={i} onClick={() => setQuery(s)}>{s}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

### Faceted Search

Filter results by multiple dimensions:

**Endpoint**: `GET /api/v1/search/facets`

```bash
curl -X GET "http://localhost:8000/api/v1/search/facets?q=tutorial" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response**:
```json
{
  "hits": [...],
  "facets": {
    "content_type_name": {
      "blog_post": 45,
      "documentation": 12,
      "tutorial": 8
    },
    "status": {
      "published": 52,
      "draft": 13
    },
    "author_id": {
      "1": 30,
      "5": 20,
      "8": 15
    }
  },
  "total": 65
}
```

**Frontend Filter UI**:
```jsx
function SearchFilters({ facets, onFilterChange }) {
  return (
    <div className="filters">
      <h4>Content Type</h4>
      {Object.entries(facets.content_type_name).map(([type, count]) => (
        <label key={type}>
          <input
            type="checkbox"
            onChange={(e) => onFilterChange('content_type', type, e.target.checked)}
          />
          {type} ({count})
        </label>
      ))}
      
      <h4>Status</h4>
      {Object.entries(facets.status).map(([status, count]) => (
        <label key={status}>
          <input
            type="checkbox"
            onChange={(e) => onFilterChange('status', status, e.target.checked)}
          />
          {status} ({count})
        </label>
      ))}
    </div>
  );
}
```

### Date Range Filtering

Filter by publication or creation date:

```bash
# Published in last 7 days
curl -X GET "http://localhost:8000/api/v1/search?q=tutorial&published_after=2025-11-19" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Published between dates
curl -X GET "http://localhost:8000/api/v1/search?q=tutorial&published_after=2025-11-01&published_before=2025-11-30" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Search Analytics

Track search behavior to improve content and relevance.

### Popular Queries

See what users are searching for:

**Endpoint**: `GET /api/v1/analytics/search/popular-queries`

```bash
curl -X GET "http://localhost:8000/api/v1/analytics/search/popular-queries?days=30&limit=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response**:
```json
{
  "queries": [
    {
      "query": "python tutorial",
      "count": 1523,
      "avg_results": 45,
      "avg_click_position": 2.3
    },
    {
      "query": "API documentation",
      "count": 892,
      "avg_results": 12,
      "avg_click_position": 1.8
    }
  ],
  "period": {
    "start": "2025-10-27",
    "end": "2025-11-26",
    "days": 30
  }
}
```

### Zero-Result Searches

Identify searches that return no results:

**Endpoint**: `GET /api/v1/analytics/search/zero-results`

```bash
curl -X GET "http://localhost:8000/api/v1/analytics/search/zero-results?days=7" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response**:
```json
{
  "queries": [
    {
      "query": "elasticsearch migration",
      "count": 23,
      "last_searched": "2025-11-25T14:30:00Z"
    },
    {
      "query": "kubernetes deployment guide",
      "count": 15,
      "last_searched": "2025-11-24T09:15:00Z"
    }
  ],
  "total": 38,
  "suggestions": [
    "Create content about 'elasticsearch migration'",
    "Add documentation for 'kubernetes deployment'"
  ]
}
```

**Use Cases**:
- Identify content gaps
- Create new content based on demand
- Improve synonyms and relevance tuning

### Click-Through Rate (CTR)

Measure how often users click search results:

**Endpoint**: `GET /api/v1/analytics/search/ctr`

```bash
curl -X GET "http://localhost:8000/api/v1/analytics/search/ctr?days=30" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response**:
```json
{
  "overall_ctr": 0.67,
  "by_query": [
    {
      "query": "python tutorial",
      "searches": 1523,
      "clicks": 1245,
      "ctr": 0.82
    },
    {
      "query": "API guide",
      "searches": 892,
      "clicks": 534,
      "ctr": 0.60
    }
  ],
  "by_content_type": [
    {
      "content_type": "blog_post",
      "ctr": 0.75
    },
    {
      "content_type": "documentation",
      "ctr": 0.85
    }
  ]
}
```

## Best Practices

### Indexing Strategies

#### 1. Index Only Necessary Fields

Don't index everything - focus on searchable content:

```python
# Good: Index title, body, excerpt
indexed_fields = ['title', 'body', 'excerpt']

# Bad: Index IDs, timestamps, internal fields
indexed_fields = ['id', 'created_at', 'internal_metadata']
```

#### 2. Use Searchable Attributes

Configure which fields are searchable vs filterable:

```python
# Searchable: Full-text search
searchable_attributes = ['title', 'body', 'excerpt']

# Filterable: Exact matching
filterable_attributes = ['status', 'content_type_id', 'author_id']

# Sortable: Ordering
sortable_attributes = ['published_at', 'created_at']
```

#### 3. Batch Indexing

Index in batches for better performance:

```python
# Good: Batch of 1000
for batch in chunks(content_entries, 1000):
    meilisearch_client.index('content_entries').add_documents(batch)

# Bad: One at a time
for entry in content_entries:
    meilisearch_client.index('content_entries').add_document(entry)
```

### Performance Optimization

#### 1. Use Filters Over Search When Possible

```python
# Fast: Exact filter
results = search(filters='status = "published"')

# Slower: Text search
results = search(q='published')
```

#### 2. Limit Result Size

```python
# Good: Reasonable limits
results = search(q='tutorial', limit=20)

# Bad: Too many results
results = search(q='tutorial', limit=1000)
```

#### 3. Implement Caching

Cache frequent searches:

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_search(query: str, filters: str = None):
    return search_api.query(q=query, filters=filters)
```

### Relevance Tuning

#### 1. Ranking Rules

Configure how Meilisearch ranks results:

```python
ranking_rules = [
    'words',        # Number of matching words
    'typo',         # Fewer typos = higher rank
    'proximity',    # Word proximity in document
    'attribute',    # Field importance
    'sort',         # Custom sorting
    'exactness',    # Exact matches first
]
```

#### 2. Attribute Weights

Prioritize certain fields:

```python
# Title matches rank higher than body matches
searchable_attributes = [
    'title',     # Weight: 100 (highest)
    'excerpt',   # Weight: 50
    'body',      # Weight: 10
]
```

#### 3. Synonyms

Add synonyms for better matching:

```python
synonyms = {
    'js': ['javascript', 'ecmascript'],
    'db': ['database', 'data store'],
    'api': ['application programming interface', 'web service']
}
```

### Multi-language Search

#### 1. Locale-Specific Indexes

Create separate indexes per locale:

```bash
# English content
content_entries_en

# Spanish content
content_entries_es

# French content
content_entries_fr
```

#### 2. Language Detection

Automatically detect query language:

```python
from langdetect import detect

def search_multilingual(query: str):
    language = detect(query)
    index_name = f'content_entries_{language}'
    return meilisearch_client.index(index_name).search(query)
```

### Security

#### 1. Tenant Isolation

Always filter by organization:

```python
# Good: Tenant-scoped
results = search(
    q='tutorial',
    filters=f'organization_id = {current_user.organization_id}'
)

# Bad: Cross-tenant leakage
results = search(q='tutorial')
```

#### 2. API Key Permissions

Use search-only API keys:

```bash
# Generate search-only key (read-only)
MEILISEARCH_SEARCH_KEY=your-search-only-key
```

#### 3. Rate Limiting

Protect against abuse:

```python
# Default: 500/hour, 50/minute
RATE_LIMIT_SEARCH=500/hour;50/minute

# Expensive autocomplete: Lower limit
RATE_LIMIT_AUTOCOMPLETE=200/hour;20/minute
```

## Troubleshooting

### Meilisearch Not Running

**Symptoms**: Connection refused errors

**Solution**:
```bash
# Check if Meilisearch is running
curl http://localhost:7700/health

# Start Meilisearch
docker-compose up -d meilisearch
# OR
brew services start meilisearch
```

### Search Returns No Results

**Symptoms**: Empty results for known content

**Solutions**:

1. **Check if content is indexed**:
```bash
curl http://localhost:7700/indexes/content_entries/documents
```

2. **Reindex content**:
```bash
curl -X POST http://localhost:8000/api/v1/search/reindex \
  -H "Authorization: Bearer YOUR_TOKEN"
```

3. **Check filters**:
```bash
# Remove filters to test
curl -X GET "http://localhost:8000/api/v1/search?q=test"
```

### Slow Search Performance

**Symptoms**: Search takes >100ms

**Solutions**:

1. **Check Meilisearch resources**:
```bash
# Monitor Meilisearch
curl http://localhost:7700/stats
```

2. **Reduce indexed fields**:
- Remove large fields from search
- Use filterable attributes instead

3. **Add caching**:
- Cache frequent queries
- Use CDN for autocomplete

4. **Optimize database**:
- Ensure proper indexes
- Batch updates instead of real-time

### Index Out of Sync

**Symptoms**: Search returns old or missing content

**Solution**:
```bash
# Full reindex
curl -X POST http://localhost:8000/api/v1/search/reindex \
  -H "Authorization: Bearer YOUR_TOKEN"

# Check index status
curl http://localhost:7700/indexes/content_entries/stats
```

## Next Steps

- 🔗 [API Reference](/api/docs) - Complete search API documentation
- 📊 [Analytics Guide](./analytics.md) - Track and analyze search behavior
- ⚡ [Performance Guide](./performance.md) - Optimize search performance
- 🔐 [Security Guide](./security.md) - Secure your search infrastructure

---

**Need Help?**
- GitHub Issues: Report bugs or request features
- Documentation: Additional guides in `/docs`
- Community: Discord server for Q&A
