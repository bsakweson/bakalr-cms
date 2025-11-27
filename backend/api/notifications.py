"""
Notification API endpoints for in-app notifications and preferences.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.api.schemas.notification import (
    EmailLogListResponse,
    EmailLogResponse,
    EmailStats,
    NotificationCreate,
    NotificationListResponse,
    NotificationMarkRead,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate,
    NotificationResponse,
    NotificationStats,
)
from backend.core.dependencies import get_current_user, get_db
from backend.core.notification_service import NotificationService
from backend.core.permissions import PermissionChecker
from backend.core.rate_limit import get_rate_limit, limiter
from backend.models.notification import (
    EmailLog,
    EmailStatus,
    Notification,
    NotificationPreference,
    NotificationType,
)
from backend.models.user import User

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# Notification Endpoints


@router.get("")
@limiter.limit(get_rate_limit())
async def list_notifications(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    unread_only: bool = Query(False, description="Show only unread notifications"),
    notification_type: Optional[str] = Query(None, description="Filter by type"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """
    Get notifications for the current user.
    Supports filtering by read status and type.
    """
    offset = (page - 1) * per_page

    notifications = NotificationService.get_user_notifications(
        db=db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        unread_only=unread_only,
        notification_type=notification_type,
        limit=per_page,
        offset=offset,
    )

    total = (
        db.query(func.count(Notification.id))
        .filter(
            Notification.user_id == current_user.id,
            Notification.organization_id == current_user.organization_id,
        )
        .scalar()
    )

    unread_count = NotificationService.get_unread_count(
        db=db, user_id=current_user.id, organization_id=current_user.organization_id
    )

    response_data = NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        page=page,
        per_page=per_page,
        unread_count=unread_count,
    )

    # Return with 'notifications' key for backward compatibility
    return {
        "notifications": response_data.items,
        "items": response_data.items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "unread_count": unread_count,
    }


@router.get("/stats", response_model=NotificationStats)
@limiter.limit(get_rate_limit())
async def get_notification_stats(
    request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get notification statistics for the current user"""
    from sqlalchemy import func

    from backend.models.notification import NotificationPriority, NotificationType

    total_count = (
        db.query(func.count(Notification.id))
        .filter(
            Notification.user_id == current_user.id,
            Notification.organization_id == current_user.organization_id,
        )
        .scalar()
    )

    unread_count = NotificationService.get_unread_count(
        db=db, user_id=current_user.id, organization_id=current_user.organization_id
    )

    # Count by type
    by_type = {}
    for ntype in NotificationType:
        count = (
            db.query(func.count(Notification.id))
            .filter(
                Notification.user_id == current_user.id,
                Notification.organization_id == current_user.organization_id,
                Notification.notification_type == ntype,
            )
            .scalar()
        )
        by_type[ntype.value] = count

    # Count by priority
    by_priority = {}
    for priority in NotificationPriority:
        count = (
            db.query(func.count(Notification.id))
            .filter(
                Notification.user_id == current_user.id,
                Notification.organization_id == current_user.organization_id,
                Notification.priority == priority,
            )
            .scalar()
        )
        by_priority[priority.value] = count

    return NotificationStats(
        total_count=total_count, unread_count=unread_count, by_type=by_type, by_priority=by_priority
    )


@router.get("/{notification_id}", response_model=NotificationResponse)
@limiter.limit(get_rate_limit())
async def get_notification(
    request: Request,
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific notification"""
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )

    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    return NotificationResponse.model_validate(notification)


@router.post("", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(get_rate_limit())
async def create_notification(
    request: Request,
    notification_data: NotificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new notification for a user.
    Requires 'notifications.create' permission (admin only).
    """
    PermissionChecker.require_permission(current_user, "notifications.create", db)

    # Use current user if user_id not provided
    target_user_id = notification_data.user_id or current_user.id

    # Handle type alias
    ntype = notification_data.notification_type
    if not ntype and notification_data.type:
        try:
            ntype = NotificationType(notification_data.type)
        except ValueError:
            ntype = NotificationType.INFO
    elif not ntype:
        ntype = NotificationType.INFO

    notification = await NotificationService.create_notification(
        db=db,
        user_id=target_user_id,
        organization_id=current_user.organization_id,
        title=notification_data.title,
        message=notification_data.message,
        notification_type=ntype,
        priority=notification_data.priority,
        action_url=notification_data.action_url,
        action_label=notification_data.action_label,
        meta_data=notification_data.meta_data,
        expires_in_days=notification_data.expires_in_days,
        send_email=notification_data.send_email,
    )

    return NotificationResponse.model_validate(notification)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
@limiter.limit(get_rate_limit())
async def mark_notification_read(
    request: Request,
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a notification as read"""
    notification = NotificationService.mark_as_read(
        db=db, notification_id=notification_id, user_id=current_user.id
    )

    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    return NotificationResponse.model_validate(notification)


@router.post("/read-all")
@router.post("/mark-all-read")
@limiter.limit(get_rate_limit())
async def mark_all_read(
    request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Mark all notifications as read"""
    count = NotificationService.mark_all_as_read(
        db=db, user_id=current_user.id, organization_id=current_user.organization_id
    )

    return {"message": f"Marked {count} notifications as read"}


@router.post("/mark-read")
@limiter.limit(get_rate_limit())
async def mark_notifications_read(
    request: Request,
    data: NotificationMarkRead,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark multiple notifications as read"""
    count = 0
    for notification_id in data.notification_ids:
        result = NotificationService.mark_as_read(
            db=db, notification_id=notification_id, user_id=current_user.id
        )
        if result:
            count += 1

    return {"message": f"Marked {count} notifications as read"}


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(get_rate_limit())
async def delete_notification(
    request: Request,
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a notification"""
    success = NotificationService.delete_notification(
        db=db, notification_id=notification_id, user_id=current_user.id
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")


# Notification Preferences


@router.get("/preferences", response_model=List[NotificationPreferenceResponse])
@limiter.limit(get_rate_limit())
async def get_notification_preferences(
    request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get all notification preferences for the current user"""
    preferences = (
        db.query(NotificationPreference)
        .filter(
            NotificationPreference.user_id == current_user.id,
            NotificationPreference.organization_id == current_user.organization_id,
        )
        .all()
    )

    return [NotificationPreferenceResponse.model_validate(p) for p in preferences]


@router.put("/preferences", response_model=NotificationPreferenceResponse)
@limiter.limit(get_rate_limit())
async def update_notification_preference(
    request: Request,
    preference_data: NotificationPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update notification preference for an event type"""
    preference = NotificationService.update_user_preference(
        db=db,
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        event_type=preference_data.event_type,
        in_app_enabled=preference_data.in_app_enabled,
        email_enabled=preference_data.email_enabled,
        digest_enabled=preference_data.digest_enabled,
        digest_frequency=preference_data.digest_frequency,
    )

    return NotificationPreferenceResponse.model_validate(preference)


# Email Logs (Admin only)


@router.get("/email-logs", response_model=EmailLogListResponse)
@limiter.limit(get_rate_limit())
async def list_email_logs(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """
    Get email delivery logs (admin only).
    Requires 'notifications.view' permission.
    """
    PermissionChecker.require_permission(current_user, "notifications.view", db)
    offset = (page - 1) * per_page

    query = db.query(EmailLog).filter(EmailLog.organization_id == current_user.organization_id)

    if status:
        query = query.filter(EmailLog.status == status)

    total = query.count()
    logs = query.order_by(EmailLog.created_at.desc()).limit(per_page).offset(offset).all()

    return EmailLogListResponse(
        items=[EmailLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/email-stats", response_model=EmailStats)
@limiter.limit(get_rate_limit())
async def get_email_stats(
    request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Get email delivery statistics (admin only).
    Requires 'notifications.view' permission.
    """
    PermissionChecker.require_permission(current_user, "notifications.view", db)
    from sqlalchemy import func

    org_id = current_user.organization_id

    total_sent = (
        db.query(func.count(EmailLog.id))
        .filter(EmailLog.organization_id == org_id, EmailLog.status == EmailStatus.SENT)
        .scalar()
    )

    total_failed = (
        db.query(func.count(EmailLog.id))
        .filter(EmailLog.organization_id == org_id, EmailLog.status == EmailStatus.FAILED)
        .scalar()
    )

    total_pending = (
        db.query(func.count(EmailLog.id))
        .filter(EmailLog.organization_id == org_id, EmailLog.status == EmailStatus.PENDING)
        .scalar()
    )

    total_opened = (
        db.query(func.count(EmailLog.id))
        .filter(EmailLog.organization_id == org_id, EmailLog.opened_at.isnot(None))
        .scalar()
    )

    total_clicked = (
        db.query(func.count(EmailLog.id))
        .filter(EmailLog.organization_id == org_id, EmailLog.clicked_at.isnot(None))
        .scalar()
    )

    open_rate = (total_opened / total_sent * 100) if total_sent > 0 else 0
    click_rate = (total_clicked / total_sent * 100) if total_sent > 0 else 0

    # Count by template
    by_template = {}
    template_counts = (
        db.query(EmailLog.template_name, func.count(EmailLog.id))
        .filter(EmailLog.organization_id == org_id)
        .group_by(EmailLog.template_name)
        .all()
    )

    for template_name, count in template_counts:
        by_template[template_name or "unknown"] = count

    return EmailStats(
        total_sent=total_sent,
        total_failed=total_failed,
        total_pending=total_pending,
        open_rate=round(open_rate, 2),
        click_rate=round(click_rate, 2),
        by_template=by_template,
    )
