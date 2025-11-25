# Performance Optimization Guide

This document describes the performance optimizations implemented in Bakalr CMS and how to monitor and improve system performance.

## Table of Contents

- [Overview](#overview)
- [Backend Performance](#backend-performance)
- [Frontend Performance](#frontend-performance)
- [Monitoring](#monitoring)
- [Load Testing](#load-testing)
- [Performance Budgets](#performance-budgets)
- [Troubleshooting](#troubleshooting)

## Overview

Bakalr CMS implements comprehensive performance optimizations across the entire stack:

- **Backend**: Query optimization, connection pooling, caching, performance monitoring
- **Frontend**: Code splitting, lazy loading, image optimization, bundle analysis
- **Infrastructure**: Docker multi-stage builds, CDN integration, compression
- **Monitoring**: Real-time metrics, Web Vitals tracking, system resource monitoring

### Performance Targets

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| API Response Time (p95) | < 200ms | > 500ms |
| Database Query Time (p95) | < 50ms | > 200ms |
| Cache Operation | < 10ms | > 50ms |
| File Upload (per MB) | < 5s | > 15s |
| Page Load (LCP) | < 2.5s | > 4.0s |
| First Input Delay (FID) | < 100ms | > 300ms |

## Backend Performance

### Query Optimization

The backend implements several query optimization strategies:

#### 1. N+1 Query Prevention

Use the `eager_load_relationships` decorator to prevent N+1 queries:

```python
from backend.core.query_optimization import eager_load_relationships

@eager_load_relationships(['roles', 'organization'])
def get_users(db: Session):
    return db.query(User).all()
```

#### 2. Batch Loading

Load multiple entities in batches to reduce database round trips:

```python
from backend.core.query_optimization import batch_load

# Load users in batches of 100
users = batch_load(db, User, user_ids, batch_size=100)
```

#### 3. Bulk Operations

Use bulk insert/update for large datasets:

```python
from backend.core.query_optimization import bulk_insert_mappings, bulk_update_mappings

# Bulk insert
mappings = [
    {"name": "User 1", "email": "user1@example.com"},
    {"name": "User 2", "email": "user2@example.com"},
]
bulk_insert_mappings(db, User, mappings)

# Bulk update
updates = [
    {"id": 1, "status": "active"},
    {"id": 2, "status": "inactive"},
]
bulk_update_mappings(db, User, updates)
```

#### 4. Query Performance Tracking

All queries over 100ms are automatically tracked:

```python
from backend.core.query_optimization import query_tracker

# Get slow queries
slow_queries = query_tracker.get_slow_queries(limit=10)
```

### Connection Pooling

The database connection pool is configured based on environment:

```python
# Production
pool_size = 20
max_overflow = 40

# Staging
pool_size = 10
max_overflow = 20

# Development
pool_size = 5
max_overflow = 10
```

**Configuration:**
- Pool timeout: 30 seconds
- Connection recycling: 1 hour
- Query timeout: 30 seconds (PostgreSQL)

**Monitoring:**

```bash
# Get pool statistics
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/metrics/database/pool
```

### Caching Strategy

Redis caching is used throughout the application:

```python
from backend.core.cache import cache

# Cache with TTL
await cache.set("key", "value", ttl=300)  # 5 minutes

# Get cached value
value = await cache.get("key")

# Delete from cache
await cache.delete("key")

# Cache with pattern
await cache.set_pattern("user:*", users)
await cache.delete_pattern("user:*")
```

**Cache TTLs:**
- User sessions: 1 hour
- Content entries: 5 minutes
- Media metadata: 30 minutes
- Search results: 2 minutes
- Translation cache: 1 day

### Performance Middleware

The `PerformanceMiddleware` automatically tracks all HTTP requests:

```python
# Automatically added in main.py
app.add_middleware(PerformanceMiddleware)
```

**Features:**
- Tracks request duration
- Adds `X-Response-Time` header
- Records endpoint statistics (avg, min, max, p95, p99)
- Tracks error rates

### Performance Monitoring API

Admin users can access performance metrics via REST API:

```bash
# Comprehensive performance report
GET /api/v1/metrics/performance

# Endpoint statistics
GET /api/v1/metrics/performance/endpoints

# Slowest endpoints
GET /api/v1/metrics/performance/slowest?limit=10

# Database pool stats
GET /api/v1/metrics/database/pool

# Slow queries
GET /api/v1/metrics/database/slow-queries?limit=10

# System metrics (CPU, memory, disk)
GET /api/v1/metrics/system

# Reset metrics
POST /api/v1/metrics/reset
```

**Example Response:**

```json
{
  "endpoints": {
    "GET /api/v1/content/entries": {
      "total_requests": 1523,
      "avg_time_ms": 87.5,
      "min_time_ms": 12.3,
      "max_time_ms": 456.7,
      "median_time_ms": 65.2,
      "p95_time_ms": 180.4,
      "p99_time_ms": 320.8,
      "error_rate": 0.013,
      "requests_per_second": 5.2
    }
  },
  "system": {
    "cpu_percent": 23.5,
    "memory": {
      "available_mb": 4096,
      "total_mb": 8192,
      "percent_used": 50.0
    },
    "process": {
      "memory_rss_mb": 156.2,
      "threads": 8,
      "connections": 12
    }
  }
}
```

## Frontend Performance

### Code Splitting

Next.js automatically code-splits pages. For component-level splitting:

```typescript
import dynamic from 'next/dynamic';

// Lazy load component
const HeavyComponent = dynamic(() => import('./HeavyComponent'), {
  loading: () => <div>Loading...</div>,
  ssr: false, // Disable SSR for client-only components
});
```

### Image Optimization

Use Next.js Image component for automatic optimization:

```typescript
import Image from 'next/image';

<Image
  src="/media/hero.jpg"
  alt="Hero image"
  width={1200}
  height={600}
  priority // Load eagerly for above-the-fold images
  placeholder="blur" // Show blur while loading
  blurDataURL="data:image/..." // Low-quality placeholder
/>
```

**Features:**
- Automatic WebP/AVIF conversion
- Responsive image sizing
- Lazy loading by default
- Blur-up placeholders

### Bundle Optimization

The Next.js configuration includes advanced webpack optimizations:

- **Code splitting**: Separates vendor, framework, and common chunks
- **Tree shaking**: Removes unused code
- **Minification**: Production builds are minified
- **Source maps**: Available in development only

**Analyze bundle size:**

```bash
# Install analyzer
npm install --save-dev @next/bundle-analyzer

# Build and analyze
ANALYZE=true npm run build
```

### Performance Monitoring

Use the built-in performance utilities:

```typescript
import { reportWebVitals, measurePerformance, markPerformance } from '@/lib/performance';

// Track Web Vitals
export function onCLS(metric: any) {
  reportWebVitals(metric);
}

// Custom measurements
markPerformance('data-fetch-start');
// ... fetch data ...
markPerformance('data-fetch-end');
measurePerformance('data-fetch', 'data-fetch-start', 'data-fetch-end');
```

**Web Vitals Tracked:**
- LCP (Largest Contentful Paint)
- FID (First Input Delay)
- CLS (Cumulative Layout Shift)
- FCP (First Contentful Paint)
- TTFB (Time to First Byte)

## Monitoring

### Real-time Monitoring

1. **Application Metrics**
   - Request rates and response times
   - Error rates and status codes
   - Database query performance
   - Cache hit rates

2. **System Metrics**
   - CPU usage
   - Memory usage
   - Disk I/O
   - Network throughput

3. **Business Metrics**
   - Active users
   - Content operations (create, read, update, delete)
   - Media uploads
   - Search queries

### Health Checks

```bash
# Liveness probe (basic health)
curl http://localhost:8000/health

# Readiness probe (dependency health)
curl http://localhost:8000/health/ready
```

### Log Analysis

```bash
# View application logs
docker-compose logs -f backend

# Filter by level
docker-compose logs backend | grep ERROR

# View slow query logs
grep "Slow query" backend/logs/*.log
```

## Load Testing

### Using Locust

Run load tests to identify performance bottlenecks:

```bash
# Install Locust
pip install locust

# Run with web UI (http://localhost:8089)
locust -f scripts/load_test.py --host=http://localhost:8000

# Run headless
locust -f scripts/load_test.py \
  --host=http://localhost:8000 \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --headless

# Test specific scenarios
locust -f scripts/load_test.py --host=http://localhost:8000 --tags read
locust -f scripts/load_test.py --host=http://localhost:8000 --tags write
locust -f scripts/load_test.py --host=http://localhost:8000 --tags admin
```

### Load Test Scenarios

1. **Read-heavy** (typical CMS usage)
   - 70% reads, 30% writes
   - 100 concurrent users
   - 5-minute duration

2. **Write-heavy** (content creation)
   - 30% reads, 70% writes
   - 50 concurrent users
   - 3-minute duration

3. **Spike test** (traffic surge)
   - Gradually increase from 10 to 500 users
   - Monitor response degradation
   - Identify breaking point

4. **Endurance test** (stability)
   - 50 concurrent users
   - 1-hour duration
   - Check for memory leaks

### Interpreting Results

**Good:**
- p95 response time < 200ms
- p99 response time < 500ms
- Error rate < 0.1%
- Throughput > 100 RPS

**Warning:**
- p95 response time 200-500ms
- p99 response time 500-1000ms
- Error rate 0.1-1%
- Throughput 50-100 RPS

**Critical:**
- p95 response time > 500ms
- p99 response time > 1000ms
- Error rate > 1%
- Throughput < 50 RPS

## Performance Budgets

### Backend Budgets

```python
PERFORMANCE_BUDGETS = {
    "api_request": 200,        # ms
    "database_query": 50,      # ms
    "cache_operation": 10,     # ms
    "file_upload": 5000,       # ms per MB
}
```

### Frontend Budgets

| Metric | Budget | Notes |
|--------|--------|-------|
| Initial JS | 200 KB | Gzipped |
| Initial CSS | 50 KB | Gzipped |
| LCP | 2.5s | 75th percentile |
| FID | 100ms | 75th percentile |
| CLS | 0.1 | 75th percentile |
| Time to Interactive | 3.8s | Mobile 3G |

## Troubleshooting

### Slow API Responses

1. **Check slow queries:**
   ```bash
   curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/v1/metrics/database/slow-queries
   ```

2. **Check endpoint performance:**
   ```bash
   curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/v1/metrics/performance/slowest
   ```

3. **Review connection pool:**
   ```bash
   curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/v1/metrics/database/pool
   ```

### High Memory Usage

1. **Check system metrics:**
   ```bash
   curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/v1/metrics/system
   ```

2. **Profile memory usage:**
   ```bash
   # Use memory_profiler
   python -m memory_profiler backend/main.py
   ```

3. **Check for connection leaks:**
   - Monitor database pool stats over time
   - Look for increasing `checked_out` connections
   - Ensure proper session cleanup

### Slow Frontend Load

1. **Analyze bundle size:**
   ```bash
   ANALYZE=true npm run build
   ```

2. **Check network waterfall:**
   - Use browser DevTools Network tab
   - Look for render-blocking resources
   - Check compression (Gzip/Brotli)

3. **Review Web Vitals:**
   - Open browser console
   - Check performance logs
   - Identify problematic components

### Database Performance

1. **Add indexes for frequently queried fields:**
   ```sql
   CREATE INDEX idx_content_status ON content_entries(status);
   CREATE INDEX idx_content_type ON content_entries(content_type_id);
   ```

2. **Analyze query plans:**
   ```sql
   EXPLAIN ANALYZE SELECT * FROM content_entries WHERE status = 'published';
   ```

3. **Optimize N+1 queries:**
   - Use `eager_load_relationships` decorator
   - Apply `selectinload` or `joinedload`
   - Check query logs for repetitive patterns

## Best Practices

1. **Always measure before optimizing**
   - Use metrics API to identify bottlenecks
   - Profile code with actual data
   - Don't optimize prematurely

2. **Use caching strategically**
   - Cache expensive operations
   - Set appropriate TTLs
   - Invalidate on updates

3. **Optimize database queries**
   - Add indexes for common queries
   - Use eager loading for relationships
   - Batch operations when possible

4. **Monitor continuously**
   - Set up alerts for performance degradation
   - Review metrics regularly
   - Track trends over time

5. **Test under load**
   - Run load tests before releases
   - Test with production-like data
   - Identify breaking points

## Resources

- [FastAPI Performance](https://fastapi.tiangolo.com/advanced/performance/)
- [Next.js Performance](https://nextjs.org/docs/advanced-features/measuring-performance)
- [Web Vitals](https://web.dev/vitals/)
- [SQLAlchemy Performance](https://docs.sqlalchemy.org/en/14/faq/performance.html)
- [PostgreSQL Performance](https://www.postgresql.org/docs/current/performance-tips.html)
