"""
Analytics API endpoints for dashboard metrics and statistics.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from backend.core.dependencies import get_current_active_user, get_db
from backend.core.rate_limit import get_rate_limit, limiter
from backend.models.audit_log import AuditLog
from backend.models.content import ContentEntry, ContentType
from backend.models.media import Media
from backend.models.user import User

router = APIRouter(prefix="/analytics", tags=["analytics"])


# Response Schemas
class ContentStatsResponse(BaseModel):
    total_entries: int
    published_entries: int
    draft_entries: int
    total_types: int
    entries_by_type: list[dict]
    recent_entries: list[dict]


class UserStatsResponse(BaseModel):
    total_users: int
    active_users_7d: int
    active_users_30d: int
    new_users_7d: int
    new_users_30d: int
    top_contributors: list[dict]


class MediaStatsResponse(BaseModel):
    total_media: int
    total_size_mb: float
    media_by_type: list[dict]
    recent_uploads: list[dict]


class ActivityStatsResponse(BaseModel):
    actions_today: int
    actions_7d: int
    actions_30d: int
    recent_activities: list[dict]
    actions_by_type: list[dict]


class TrendDataPoint(BaseModel):
    date: str
    value: int


class TrendsResponse(BaseModel):
    content_trend: list[TrendDataPoint]
    user_trend: list[TrendDataPoint]
    activity_trend: list[TrendDataPoint]


class DashboardOverviewResponse(BaseModel):
    content_stats: ContentStatsResponse
    user_stats: UserStatsResponse
    media_stats: MediaStatsResponse
    activity_stats: ActivityStatsResponse


@router.get("/content", response_model=ContentStatsResponse)
@limiter.limit(get_rate_limit())
async def get_content_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get content statistics for the current organization."""
    org_id = current_user.organization_id

    # Total entries (join with content_type to filter by organization)
    total_entries = (
        db.query(ContentEntry)
        .join(ContentType)
        .filter(ContentType.organization_id == org_id)
        .count()
    )

    # Published vs Draft
    published_entries = (
        db.query(ContentEntry)
        .join(ContentType)
        .filter(and_(ContentType.organization_id == org_id, ContentEntry.status == "published"))
        .count()
    )

    draft_entries = (
        db.query(ContentEntry)
        .join(ContentType)
        .filter(and_(ContentType.organization_id == org_id, ContentEntry.status == "draft"))
        .count()
    )

    # Total content types
    total_types = db.query(ContentType).filter(ContentType.organization_id == org_id).count()

    # Entries by type
    entries_by_type = (
        db.query(ContentType.name, func.count(ContentEntry.id).label("count"))
        .join(ContentEntry, ContentEntry.content_type_id == ContentType.id)
        .filter(ContentType.organization_id == org_id)
        .group_by(ContentType.name)
        .all()
    )

    entries_by_type_list = [{"type": row[0], "count": row[1]} for row in entries_by_type]

    # Recent entries (last 10)
    recent_entries = (
        db.query(ContentEntry)
        .join(ContentType)
        .filter(ContentType.organization_id == org_id)
        .order_by(desc(ContentEntry.created_at))
        .limit(10)
        .all()
    )

    recent_entries_list = []
    for entry in recent_entries:
        # Parse data if it's a JSON string
        data = entry.data
        if isinstance(data, str):
            try:
                import json

                data = json.loads(data)
            except:
                data = {}
        elif data is None:
            data = {}

        recent_entries_list.append(
            {
                "id": entry.id,
                "title": data.get("title", "Untitled"),
                "status": entry.status,
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
            }
        )

    return ContentStatsResponse(
        total_entries=total_entries,
        published_entries=published_entries,
        draft_entries=draft_entries,
        total_types=total_types,
        entries_by_type=entries_by_type_list,
        recent_entries=recent_entries_list,
    )


@router.get("/users", response_model=UserStatsResponse)
@limiter.limit(get_rate_limit())
async def get_user_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get user statistics for the current organization."""
    org_id = current_user.organization_id
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    # Total users
    total_users = db.query(User).filter(User.organization_id == org_id).count()

    # New users in last 7 and 30 days
    new_users_7d = (
        db.query(User)
        .filter(and_(User.organization_id == org_id, User.created_at >= seven_days_ago))
        .count()
    )

    new_users_30d = (
        db.query(User)
        .filter(and_(User.organization_id == org_id, User.created_at >= thirty_days_ago))
        .count()
    )

    # Active users (users with audit log entries in last 7/30 days)
    active_users_7d = (
        db.query(func.count(func.distinct(AuditLog.user_id)))
        .filter(
            and_(
                AuditLog.organization_id == org_id,
                AuditLog.created_at >= seven_days_ago,
                AuditLog.user_id.isnot(None),
            )
        )
        .scalar()
        or 0
    )

    active_users_30d = (
        db.query(func.count(func.distinct(AuditLog.user_id)))
        .filter(
            and_(
                AuditLog.organization_id == org_id,
                AuditLog.created_at >= thirty_days_ago,
                AuditLog.user_id.isnot(None),
            )
        )
        .scalar()
        or 0
    )

    # Top contributors (users with most content entries)
    top_contributors = (
        db.query(
            User.id,
            User.first_name,
            User.last_name,
            User.email,
            func.count(ContentEntry.id).label("entries_count"),
        )
        .join(ContentEntry, ContentEntry.author_id == User.id)
        .filter(User.organization_id == org_id)
        .group_by(User.id, User.first_name, User.last_name, User.email)
        .order_by(desc("entries_count"))
        .limit(5)
        .all()
    )

    top_contributors_list = [
        {
            "id": row[0],
            "name": f"{row[1] or ''} {row[2] or ''}".strip() or row[3],
            "email": row[3],
            "entries_count": row[4],
        }
        for row in top_contributors
    ]

    return UserStatsResponse(
        total_users=total_users,
        active_users_7d=active_users_7d,
        active_users_30d=active_users_30d,
        new_users_7d=new_users_7d,
        new_users_30d=new_users_30d,
        top_contributors=top_contributors_list,
    )


@router.get("/media", response_model=MediaStatsResponse)
@limiter.limit(get_rate_limit())
async def get_media_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get media statistics for the current organization."""
    org_id = current_user.organization_id

    # Total media files
    total_media = db.query(Media).filter(Media.organization_id == org_id).count()

    # Total size in MB
    total_size_bytes = (
        db.query(func.sum(Media.size)).filter(Media.organization_id == org_id).scalar() or 0
    )
    total_size_mb = round(total_size_bytes / (1024 * 1024), 2)

    # Media by type
    media_by_type = (
        db.query(Media.mime_type, func.count(Media.id).label("count"))
        .filter(Media.organization_id == org_id)
        .group_by(Media.mime_type)
        .all()
    )

    media_by_type_list = [{"type": row[0], "count": row[1]} for row in media_by_type]

    # Recent uploads (last 10)
    recent_uploads = (
        db.query(Media)
        .filter(Media.organization_id == org_id)
        .order_by(desc(Media.created_at))
        .limit(10)
        .all()
    )

    recent_uploads_list = [
        {
            "id": media.id,
            "filename": media.filename,
            "mime_type": media.mime_type,
            "size": media.size,
            "created_at": media.created_at.isoformat() if media.created_at else None,
        }
        for media in recent_uploads
    ]

    return MediaStatsResponse(
        total_media=total_media,
        total_size_mb=total_size_mb,
        media_by_type=media_by_type_list,
        recent_uploads=recent_uploads_list,
    )


@router.get("/activity", response_model=ActivityStatsResponse)
@limiter.limit(get_rate_limit())
async def get_activity_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get activity statistics for the current organization."""
    org_id = current_user.organization_id
    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    # Actions today
    actions_today = (
        db.query(AuditLog)
        .filter(and_(AuditLog.organization_id == org_id, AuditLog.created_at >= today_start))
        .count()
    )

    # Actions in last 7 days
    actions_7d = (
        db.query(AuditLog)
        .filter(and_(AuditLog.organization_id == org_id, AuditLog.created_at >= seven_days_ago))
        .count()
    )

    # Actions in last 30 days
    actions_30d = (
        db.query(AuditLog)
        .filter(and_(AuditLog.organization_id == org_id, AuditLog.created_at >= thirty_days_ago))
        .count()
    )

    # Recent activities (last 20)
    recent_activities = (
        db.query(AuditLog)
        .join(User, User.id == AuditLog.user_id, isouter=True)
        .filter(AuditLog.organization_id == org_id)
        .order_by(desc(AuditLog.created_at))
        .limit(20)
        .all()
    )

    recent_activities_list = [
        {
            "id": activity.id,
            "action": activity.action,
            "resource_type": activity.resource_type,
            "description": activity.description,
            "user_name": activity.user.full_name if activity.user else "System",
            "created_at": activity.created_at.isoformat() if activity.created_at else None,
        }
        for activity in recent_activities
    ]

    # Actions by type
    actions_by_type = (
        db.query(AuditLog.action, func.count(AuditLog.id).label("count"))
        .filter(and_(AuditLog.organization_id == org_id, AuditLog.created_at >= thirty_days_ago))
        .group_by(AuditLog.action)
        .order_by(desc("count"))
        .limit(10)
        .all()
    )

    actions_by_type_list = [{"action": row[0], "count": row[1]} for row in actions_by_type]

    return ActivityStatsResponse(
        actions_today=actions_today,
        actions_7d=actions_7d,
        actions_30d=actions_30d,
        recent_activities=recent_activities_list,
        actions_by_type=actions_by_type_list,
    )


@router.get("/trends", response_model=TrendsResponse)
@limiter.limit(get_rate_limit())
async def get_trends(
    request: Request,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get trend data for charts (last N days)."""
    org_id = current_user.organization_id
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)

    # Generate date range
    date_range = []
    for i in range(days + 1):
        date = start_date + timedelta(days=i)
        date_range.append(date.date())

    # Content trend (entries created per day)
    content_trend_data = {}
    content_entries = (
        db.query(
            func.date(ContentEntry.created_at).label("date"),
            func.count(ContentEntry.id).label("count"),
        )
        .join(ContentType)
        .filter(and_(ContentType.organization_id == org_id, ContentEntry.created_at >= start_date))
        .group_by(func.date(ContentEntry.created_at))
        .all()
    )

    for row in content_entries:
        content_trend_data[row[0]] = row[1]

    content_trend = [
        TrendDataPoint(date=str(date), value=content_trend_data.get(date, 0)) for date in date_range
    ]

    # User trend (users created per day)
    user_trend_data = {}
    users = (
        db.query(func.date(User.created_at).label("date"), func.count(User.id).label("count"))
        .filter(and_(User.organization_id == org_id, User.created_at >= start_date))
        .group_by(func.date(User.created_at))
        .all()
    )

    for row in users:
        user_trend_data[row[0]] = row[1]

    user_trend = [
        TrendDataPoint(date=str(date), value=user_trend_data.get(date, 0)) for date in date_range
    ]

    # Activity trend (actions per day)
    activity_trend_data = {}
    activities = (
        db.query(
            func.date(AuditLog.created_at).label("date"), func.count(AuditLog.id).label("count")
        )
        .filter(and_(AuditLog.organization_id == org_id, AuditLog.created_at >= start_date))
        .group_by(func.date(AuditLog.created_at))
        .all()
    )

    for row in activities:
        activity_trend_data[row[0]] = row[1]

    activity_trend = [
        TrendDataPoint(date=str(date), value=activity_trend_data.get(date, 0))
        for date in date_range
    ]

    return TrendsResponse(
        content_trend=content_trend, user_trend=user_trend, activity_trend=activity_trend
    )


@router.get("/overview", response_model=DashboardOverviewResponse)
@limiter.limit(get_rate_limit())
async def get_dashboard_overview(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get all analytics data for the dashboard overview."""
    content_stats = await get_content_stats(request, db, current_user)
    user_stats = await get_user_stats(request, db, current_user)
    media_stats = await get_media_stats(request, db, current_user)
    activity_stats = await get_activity_stats(request, db, current_user)

    return DashboardOverviewResponse(
        content_stats=content_stats,
        user_stats=user_stats,
        media_stats=media_stats,
        activity_stats=activity_stats,
    )
