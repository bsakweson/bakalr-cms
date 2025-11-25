"""
Database query optimization utilities and decorators
"""
from functools import wraps
from typing import Callable, Any
from sqlalchemy.orm import Query, Session, joinedload, selectinload, lazyload
from sqlalchemy import event
import time
import logging

logger = logging.getLogger(__name__)

# Query performance tracking
class QueryPerformanceTracker:
    """Track slow queries for optimization"""
    
    def __init__(self, threshold_ms: float = 100):
        self.threshold_ms = threshold_ms
        self.slow_queries = []
    
    def track_query(self, statement: str, duration_ms: float):
        """Track a query execution"""
        if duration_ms > self.threshold_ms:
            self.slow_queries.append({
                "statement": statement,
                "duration_ms": duration_ms,
                "timestamp": time.time()
            })
            logger.warning(f"Slow query detected ({duration_ms:.2f}ms): {statement[:200]}")
    
    def get_slow_queries(self, limit: int = 10):
        """Get recent slow queries"""
        return sorted(
            self.slow_queries,
            key=lambda x: x["duration_ms"],
            reverse=True
        )[:limit]
    
    def clear(self):
        """Clear tracked queries"""
        self.slow_queries.clear()


# Global tracker instance
query_tracker = QueryPerformanceTracker(threshold_ms=100)


def setup_query_logging(engine):
    """Set up query performance logging"""
    
    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        conn.info.setdefault("query_start_time", []).append(time.time())
    
    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        total_time = time.time() - conn.info["query_start_time"].pop()
        duration_ms = total_time * 1000
        query_tracker.track_query(statement, duration_ms)


def optimize_query(query: Query) -> Query:
    """
    Apply common optimization strategies to a query
    """
    # Enable result caching for read queries
    return query.execution_options(
        compiled_cache={},
        synchronize_session='fetch'
    )


def eager_load_relationships(*relationships):
    """
    Decorator to prevent N+1 queries by eager loading relationships
    
    Usage:
        @eager_load_relationships('user', 'organization')
        def get_content_entries(db: Session):
            return db.query(ContentEntry).all()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # If result is a query, apply eager loading
            if isinstance(result, Query):
                for rel in relationships:
                    result = result.options(selectinload(rel))
            
            return result
        
        return wrapper
    
    return decorator


def batch_load(session: Session, model, ids: list, batch_size: int = 100):
    """
    Batch load entities to prevent N+1 queries
    
    Usage:
        users = batch_load(db, User, user_ids)
    """
    results = []
    for i in range(0, len(ids), batch_size):
        batch = ids[i:i + batch_size]
        results.extend(session.query(model).filter(model.id.in_(batch)).all())
    return results


class QueryOptimizer:
    """Context manager for query optimization"""
    
    def __init__(self, session: Session):
        self.session = session
        self.original_autoflush = session.autoflush
    
    def __enter__(self):
        """Disable autoflush for bulk operations"""
        self.session.autoflush = False
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore autoflush and commit if needed"""
        self.session.autoflush = self.original_autoflush
        if exc_type is None:
            self.session.flush()


def bulk_insert_mappings(session: Session, model, data: list, batch_size: int = 1000):
    """
    Efficient bulk insert using SQLAlchemy bulk operations
    
    Usage:
        bulk_insert_mappings(db, User, [
            {"email": "user1@example.com", "name": "User 1"},
            {"email": "user2@example.com", "name": "User 2"},
        ])
    """
    with QueryOptimizer(session):
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            session.bulk_insert_mappings(model, batch)
        session.commit()


def bulk_update_mappings(session: Session, model, data: list, batch_size: int = 1000):
    """
    Efficient bulk update using SQLAlchemy bulk operations
    
    Usage:
        bulk_update_mappings(db, User, [
            {"id": 1, "name": "Updated Name 1"},
            {"id": 2, "name": "Updated Name 2"},
        ])
    """
    with QueryOptimizer(session):
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            session.bulk_update_mappings(model, batch)
        session.commit()


# Query hints for different scenarios
class LoadStrategy:
    """Common loading strategies for relationships"""
    
    @staticmethod
    def immediate(*relationships):
        """Load relationships immediately with joined load"""
        return [joinedload(rel) for rel in relationships]
    
    @staticmethod
    def separate(*relationships):
        """Load relationships in separate queries"""
        return [selectinload(rel) for rel in relationships]
    
    @staticmethod
    def lazy(*relationships):
        """Lazy load relationships (default behavior)"""
        return [lazyload(rel) for rel in relationships]


# Performance best practices documentation
OPTIMIZATION_TIPS = """
Database Query Optimization Best Practices:

1. PREVENT N+1 QUERIES:
   - Use selectinload() for one-to-many relationships
   - Use joinedload() for many-to-one relationships
   - Avoid accessing relationships in loops

2. USE PAGINATION:
   - Always paginate large result sets
   - Use limit() and offset() with proper indexing
   - Consider cursor-based pagination for large datasets

3. SELECT ONLY NEEDED COLUMNS:
   - Use defer() to skip loading large columns
   - Use load_only() to load specific columns
   - Avoid SELECT * when possible

4. BATCH OPERATIONS:
   - Use bulk_insert_mappings() for bulk inserts
   - Use bulk_update_mappings() for bulk updates
   - Group database operations together

5. USE INDEXES:
   - Index foreign keys
   - Index columns used in WHERE clauses
   - Index columns used in ORDER BY
   - Use composite indexes for multiple columns

6. CACHE RESULTS:
   - Cache frequently accessed data in Redis
   - Use ETags for HTTP caching
   - Implement query result caching

7. OPTIMIZE JOINS:
   - Limit the number of joins in a single query
   - Use subqueries when appropriate
   - Consider denormalization for read-heavy workloads

8. MONITOR PERFORMANCE:
   - Use query_tracker to identify slow queries
   - Set up database query logging
   - Profile critical endpoints regularly
"""


def print_optimization_tips():
    """Print optimization tips for developers"""
    print(OPTIMIZATION_TIPS)
