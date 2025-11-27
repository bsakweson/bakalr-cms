"""
Audit Log API endpoints for viewing activity history
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_organization, get_current_user
from backend.core.permissions import PermissionChecker
from backend.core.rate_limit import get_rate_limit, limiter
from backend.db.session import get_db
from backend.models.audit_log import AuditLog
from backend.models.organization import Organization
from backend.models.user import User

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


# Response schemas
class AuditLogItem(BaseModel):
    id: int
    action: str
    resource_type: str
    resource_id: Optional[int]
    description: Optional[str]
    severity: str
    status: str
    user_id: Optional[int]
    user_email: Optional[str]
    user_name: Optional[str]
    ip_address: Optional[str]
    created_at: str


class AuditLogListResponse(BaseModel):
    logs: List[AuditLogItem]
    total: int
    page: int
    page_size: int


class AuditLogStatsResponse(BaseModel):
    total_logs: int
    actions_today: int
    failed_actions: int
    unique_users: int


@router.get("/", response_model=AuditLogListResponse)
@limiter.limit(get_rate_limit())
async def list_audit_logs(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    user_id: Optional[int] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    days: Optional[int] = Query(7, ge=1, le=90),
    org: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get audit logs with filtering and pagination
    """
    PermissionChecker.require_permission(current_user, "view_audit_logs", db)
    # Base query
    query = db.query(AuditLog).filter(AuditLog.organization_id == org.id)

    # Date filter
    if days:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        query = query.filter(AuditLog.created_at >= cutoff_date)

    # Apply filters
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if severity:
        query = query.filter(AuditLog.severity == severity)
    if status:
        query = query.filter(AuditLog.status == status)

    # Get total count
    total = query.count()

    # Paginate and order by newest first
    logs = (
        query.order_by(desc(AuditLog.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Build response
    log_items = []
    for log in logs:
        user_email = None
        user_name = None
        if log.user:
            user_email = log.user.email
            user_name = f"{log.user.first_name} {log.user.last_name}".strip() or log.user.username

        log_items.append(
            AuditLogItem(
                id=log.id,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                description=log.description,
                severity=log.severity,
                status=log.status,
                user_id=log.user_id,
                user_email=user_email,
                user_name=user_name,
                ip_address=log.ip_address,
                created_at=log.created_at.isoformat() if log.created_at else "",
            )
        )

    return AuditLogListResponse(logs=log_items, total=total, page=page, page_size=page_size)


@router.get("/stats", response_model=AuditLogStatsResponse)
@limiter.limit(get_rate_limit())
async def get_audit_stats(
    request: Request,
    org: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get audit log statistics
    """
    PermissionChecker.require_permission(current_user, "view_audit_logs", db)
    # Total logs
    total_logs = db.query(AuditLog).filter(AuditLog.organization_id == org.id).count()

    # Actions today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    actions_today = (
        db.query(AuditLog)
        .filter(AuditLog.organization_id == org.id, AuditLog.created_at >= today_start)
        .count()
    )

    # Failed actions (last 7 days)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    failed_actions = (
        db.query(AuditLog)
        .filter(
            AuditLog.organization_id == org.id,
            AuditLog.status == "failure",
            AuditLog.created_at >= week_ago,
        )
        .count()
    )

    # Unique users (last 30 days)
    month_ago = datetime.now(timezone.utc) - timedelta(days=30)
    unique_users = (
        db.query(AuditLog.user_id)
        .filter(
            AuditLog.organization_id == org.id,
            AuditLog.user_id.isnot(None),
            AuditLog.created_at >= month_ago,
        )
        .distinct()
        .count()
    )

    return AuditLogStatsResponse(
        total_logs=total_logs,
        actions_today=actions_today,
        failed_actions=failed_actions,
        unique_users=unique_users,
    )
