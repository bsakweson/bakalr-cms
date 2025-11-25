"""
Database session management with optimized connection pooling
"""
from typing import Generator
from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
import logging

from backend.core.config import settings

logger = logging.getLogger(__name__)

# Connection pool configuration based on environment
if settings.ENVIRONMENT == "production":
    # Production: Larger pool for handling concurrent requests
    POOL_SIZE = 20
    MAX_OVERFLOW = 40
    POOL_TIMEOUT = 30
    POOL_RECYCLE = 3600  # Recycle connections after 1 hour
elif settings.ENVIRONMENT == "staging":
    # Staging: Medium pool
    POOL_SIZE = 10
    MAX_OVERFLOW = 20
    POOL_TIMEOUT = 30
    POOL_RECYCLE = 3600
else:
    # Development: Smaller pool
    POOL_SIZE = 5
    MAX_OVERFLOW = 10
    POOL_TIMEOUT = 30
    POOL_RECYCLE = 3600

# Create database engine with optimized pooling
engine_kwargs = {
    "echo": settings.DATABASE_ECHO,
    "pool_pre_ping": True,  # Verify connections before using
    "pool_size": POOL_SIZE,
    "max_overflow": MAX_OVERFLOW,
    "pool_timeout": POOL_TIMEOUT,
    "pool_recycle": POOL_RECYCLE,
    "connect_args": {
        "connect_timeout": 10,
        # PostgreSQL-specific optimizations
        "options": "-c statement_timeout=30000"  # 30 second query timeout
    } if "postgresql" in settings.DATABASE_URL else {}
}

# Use QueuePool for better performance
if "sqlite" not in settings.DATABASE_URL:
    engine_kwargs["poolclass"] = pool.QueuePool

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

# Set up query performance logging
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Set SQLite pragmas for better performance"""
    if "sqlite" in settings.DATABASE_URL:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
        cursor.execute("PRAGMA synchronous=NORMAL")  # Faster writes
        cursor.execute("PRAGMA cache_size=10000")  # 10MB cache
        cursor.execute("PRAGMA temp_store=MEMORY")  # Use memory for temp tables
        cursor.close()

# Log pool statistics in development
if settings.DEBUG:
    @event.listens_for(engine, "connect")
    def log_connection(dbapi_conn, connection_record):
        logger.debug(f"Database connection established: {id(dbapi_conn)}")
    
    @event.listens_for(engine, "close")
    def log_close(dbapi_conn, connection_record):
        logger.debug(f"Database connection closed: {id(dbapi_conn)}")

# Create session factory with optimizations
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Don't expire objects after commit for better performance
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database session with proper cleanup
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        db.close()


def get_pool_stats():
    """Get connection pool statistics for monitoring"""
    return {
        "pool_size": engine.pool.size(),
        "checked_in": engine.pool.checkedin(),
        "checked_out": engine.pool.checkedout(),
        "overflow": engine.pool.overflow(),
        "total_connections": engine.pool.size() + engine.pool.overflow()
    }
