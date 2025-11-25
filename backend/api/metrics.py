"""
Performance and metrics API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core.performance import performance_monitor, get_performance_report
from backend.core.query_optimization import query_tracker
from backend.db.session import get_pool_stats, SessionLocal
from backend.core.permissions import PermissionChecker
from backend.api.auth import get_current_user
from backend.models.user import User

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/performance")
async def get_performance_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(SessionLocal)
):
    """
    Get comprehensive performance metrics
    Requires admin.metrics permission
    """
    PermissionChecker.require_permission(current_user, "admin.metrics", db)
    return get_performance_report()


@router.get("/performance/endpoints")
async def get_endpoint_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(SessionLocal)
):
    """
    Get performance metrics for all endpoints
    Requires admin.metrics permission
    """
    PermissionChecker.require_permission(current_user, "admin.metrics", db)
    return {
        "endpoints": performance_monitor.get_endpoint_stats()
    }


@router.get("/performance/slowest")
async def get_slowest_endpoints(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(SessionLocal)
):
    """
    Get the slowest endpoints by average response time
    Requires admin.metrics permission
    """
    PermissionChecker.require_permission(current_user, "admin.metrics", db)
    return {
        "slowest_endpoints": performance_monitor.get_slowest_endpoints(limit=limit)
    }


@router.get("/database/pool")
async def get_database_pool_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(SessionLocal)
):
    """
    Get database connection pool statistics
    Requires admin.metrics permission
    """
    PermissionChecker.require_permission(current_user, "admin.metrics", db)
    try:
        stats = get_pool_stats()
        return {
            "pool_stats": stats,
            "health": "healthy" if stats["checked_out"] < stats["pool_size"] else "degraded"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/database/slow-queries")
async def get_slow_queries(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(SessionLocal)
):
    """
    Get recent slow database queries
    Requires admin.metrics permission
    """
    PermissionChecker.require_permission(current_user, "admin.metrics", db)
    return {
        "slow_queries": query_tracker.get_slow_queries(limit=limit)
    }


@router.get("/system")
async def get_system_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(SessionLocal)
):
    """
    Get system resource metrics (CPU, memory, disk)
    Requires admin.metrics permission
    """
    PermissionChecker.require_permission(current_user, "admin.metrics", db)
    return performance_monitor.get_system_metrics()


@router.post("/reset")
async def reset_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(SessionLocal)
):
    """
    Reset all performance metrics
    Requires admin.metrics permission
    """
    PermissionChecker.require_permission(current_user, "admin.metrics", db)
    performance_monitor.reset_stats()
    query_tracker.slow_queries.clear()
    
    return {
        "status": "success",
        "message": "Performance metrics reset successfully"
    }
