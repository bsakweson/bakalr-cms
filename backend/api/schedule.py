"""
Content Scheduling API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.schedule import (
    ScheduleContentRequest,
    ScheduleContentResponse,
    ScheduleListResponse,
)
from backend.core.dependencies import get_current_user
from backend.core.rate_limit import get_rate_limit, limiter
from backend.core.scheduling_service import SchedulingService
from backend.db.session import get_db
from backend.models.content import ContentEntry
from backend.models.schedule import ContentSchedule
from backend.models.user import User

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.post("/content/{content_entry_id}", response_model=ScheduleContentResponse)
@limiter.limit(get_rate_limit())
async def schedule_content_action(
    request_obj: Request,
    content_entry_id: int,
    request: ScheduleContentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Schedule a publish or unpublish action for content.
    Supports timezone-aware scheduling.
    """
    # Verify content entry exists and belongs to user's organization
    result = await db.execute(
        select(ContentEntry)
        .join(ContentEntry.content_type)
        .where(
            ContentEntry.id == content_entry_id,
            ContentEntry.content_type.has(organization_id=current_user.organization_id),
        )
    )
    content_entry = result.scalar_one_or_none()

    if not content_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content entry not found")

    # Create schedule
    schedule = await SchedulingService.create_schedule(
        db=db,
        content_entry_id=content_entry_id,
        organization_id=current_user.organization_id,
        action=request.action,
        scheduled_at=request.scheduled_at,
    )

    return ScheduleContentResponse(
        id=schedule.id,
        content_entry_id=schedule.content_entry_id,
        action=schedule.action,
        scheduled_at=schedule.scheduled_at,
        status=schedule.status,
        created_at=schedule.created_at,
        executed_at=schedule.executed_at,
        error_message=schedule.error_message,
    )


@router.get("/content/{content_entry_id}", response_model=ScheduleListResponse)
@limiter.limit(get_rate_limit())
async def get_content_schedules(
    request: Request,
    content_entry_id: int,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all schedules for a content entry.
    """
    # Verify content entry exists and belongs to user's organization
    result = await db.execute(
        select(ContentEntry)
        .join(ContentEntry.content_type)
        .where(
            ContentEntry.id == content_entry_id,
            ContentEntry.content_type.has(organization_id=current_user.organization_id),
        )
    )
    content_entry = result.scalar_one_or_none()

    if not content_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content entry not found")

    # Get schedules
    offset = (page - 1) * page_size

    # Get total count
    count_result = await db.execute(
        select(ContentSchedule).where(ContentSchedule.content_entry_id == content_entry_id)
    )
    total = len(list(count_result.scalars().all()))

    # Get paginated schedules
    result = await db.execute(
        select(ContentSchedule)
        .where(ContentSchedule.content_entry_id == content_entry_id)
        .order_by(ContentSchedule.scheduled_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    schedules = result.scalars().all()

    items = [
        ScheduleContentResponse(
            id=schedule.id,
            content_entry_id=schedule.content_entry_id,
            action=schedule.action,
            scheduled_at=schedule.scheduled_at,
            status=schedule.status,
            created_at=schedule.created_at,
            executed_at=schedule.executed_at,
            error_message=schedule.error_message,
        )
        for schedule in schedules
    ]

    return ScheduleListResponse(items=items, total=total, page=page, page_size=page_size)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(get_rate_limit())
async def cancel_schedule(
    request: Request,
    schedule_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel a pending schedule.
    """
    schedule = await SchedulingService.cancel_schedule(
        db=db, schedule_id=schedule_id, organization_id=current_user.organization_id
    )

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found or already executed"
        )

    return None


@router.post("/execute-pending", status_code=status.HTTP_200_OK)
@limiter.limit(get_rate_limit())
async def execute_pending_schedules(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger execution of pending schedules.
    Typically called by a cron job or background worker.

    Note: In production, this should be secured with admin-only access.
    """
    # Get pending schedules
    schedules = await SchedulingService.get_pending_schedules(db=db)

    executed_count = 0
    failed_count = 0

    for schedule in schedules:
        success = await SchedulingService.execute_schedule(db=db, schedule=schedule)
        if success:
            executed_count += 1
        else:
            failed_count += 1

    return {
        "message": "Pending schedules processed",
        "executed": executed_count,
        "failed": failed_count,
        "total": len(schedules),
    }
