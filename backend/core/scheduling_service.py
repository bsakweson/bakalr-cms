"""
Content scheduling service for scheduled publish/unpublish actions.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.schedule import ContentSchedule
from backend.models.content import ContentEntry


class SchedulingService:
    """Service for managing content scheduling."""
    
    @staticmethod
    async def create_schedule(
        db: AsyncSession,
        content_entry_id: int,
        organization_id: int,
        action: str,
        scheduled_at: datetime
    ) -> ContentSchedule:
        """
        Create a new content schedule.
        
        Args:
            db: Database session
            content_entry_id: ID of the content entry
            organization_id: ID of the organization
            action: Action to schedule ('publish' or 'unpublish')
            scheduled_at: When to execute the action
            
        Returns:
            Created ContentSchedule instance
        """
        schedule = ContentSchedule(
            content_entry_id=content_entry_id,
            organization_id=organization_id,
            action=action,
            scheduled_at=scheduled_at,
            status="pending"
        )
        
        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)
        
        return schedule
    
    @staticmethod
    async def get_pending_schedules(
        db: AsyncSession,
        current_time: Optional[datetime] = None
    ) -> list[ContentSchedule]:
        """
        Get all pending schedules that are due for execution.
        
        Args:
            db: Database session
            current_time: Time to compare against (defaults to now)
            
        Returns:
            List of due ContentSchedule instances
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        
        result = await db.execute(
            select(ContentSchedule)
            .where(
                ContentSchedule.status == "pending",
                ContentSchedule.scheduled_at <= current_time
            )
            .order_by(ContentSchedule.scheduled_at)
        )
        
        return list(result.scalars().all())
    
    @staticmethod
    async def execute_schedule(
        db: AsyncSession,
        schedule: ContentSchedule
    ) -> bool:
        """
        Execute a scheduled action.
        
        Args:
            db: Database session
            schedule: ContentSchedule to execute
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the content entry
            result = await db.execute(
                select(ContentEntry).where(ContentEntry.id == schedule.content_entry_id)
            )
            content_entry = result.scalar_one_or_none()
            
            if not content_entry:
                schedule.status = "failed"
                schedule.error_message = "Content entry not found"
                schedule.executed_at = datetime.now(timezone.utc)
                await db.commit()
                return False
            
            # Execute the action
            if schedule.action == "publish":
                content_entry.status = "published"
                content_entry.published_at = datetime.now(timezone.utc).isoformat()
            elif schedule.action == "unpublish":
                content_entry.status = "draft"
            
            # Mark schedule as completed
            schedule.status = "completed"
            schedule.executed_at = datetime.now(timezone.utc)
            
            await db.commit()
            return True
            
        except Exception as e:
            schedule.status = "failed"
            schedule.error_message = str(e)
            schedule.executed_at = datetime.now(timezone.utc)
            await db.commit()
            return False
    
    @staticmethod
    async def cancel_schedule(
        db: AsyncSession,
        schedule_id: int,
        organization_id: int
    ) -> Optional[ContentSchedule]:
        """
        Cancel a pending schedule.
        
        Args:
            db: Database session
            schedule_id: ID of the schedule to cancel
            organization_id: Organization ID for authorization
            
        Returns:
            Updated ContentSchedule if found and cancelled, None otherwise
        """
        result = await db.execute(
            select(ContentSchedule).where(
                ContentSchedule.id == schedule_id,
                ContentSchedule.organization_id == organization_id,
                ContentSchedule.status == "pending"
            )
        )
        schedule = result.scalar_one_or_none()
        
        if schedule:
            schedule.status = "cancelled"
            await db.commit()
            await db.refresh(schedule)
        
        return schedule
