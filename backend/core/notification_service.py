"""
In-app notification service for real-time user notifications.
Manages notification creation, delivery, and read status tracking.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from backend.models.notification import (
    Notification, NotificationType, NotificationPriority,
    NotificationPreference
)
from backend.models.user import User
from backend.core.email_service import email_service


class NotificationService:
    """
    Service for managing in-app notifications and user preferences.
    Supports notification creation, delivery, and email integration.
    """
    
    @staticmethod
    async def create_notification(
        db: Session,
        user_id: int,
        organization_id: int,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        action_url: Optional[str] = None,
        action_label: Optional[str] = None,
        meta_data: Optional[Dict[str, Any]] = None,
        expires_in_days: Optional[int] = 30,
        send_email: bool = False
    ) -> Notification:
        """
        Create a new notification for a user.
        
        Args:
            db: Database session
            user_id: Target user ID
            organization_id: Organization ID
            title: Notification title
            message: Notification message
            notification_type: Type of notification (info, success, warning, error, etc.)
            priority: Priority level (low, normal, high, urgent)
            action_url: Optional URL to navigate to
            action_label: Optional action button label
            meta_data: Optional metadata dictionary
            expires_in_days: Days until notification expires (None = never)
            send_email: Whether to also send email notification
            
        Returns:
            Created notification
        """
        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        # Create notification
        notification = Notification(
            user_id=user_id,
            organization_id=organization_id,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            action_url=action_url,
            action_label=action_label,
            meta_data=meta_data,
            expires_at=expires_at
        )
        
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        # Send email if requested and user has email notifications enabled
        if send_email:
            preference = NotificationService.get_user_preference(
                db, user_id, organization_id, "general"
            )
            
            if not preference or preference.email_enabled:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    try:
                        await email_service.send_notification_email(
                            to_email=user.email,
                            user_name=f"{user.first_name or user.email}",
                            notification_title=title,
                            notification_message=message,
                            action_url=action_url,
                            organization_id=organization_id,
                            user_id=user_id
                        )
                    except Exception as e:
                        # Log email error but don't fail notification creation
                        print(f"Failed to send notification email: {e}")
        
        return notification
    
    @staticmethod
    def get_user_notifications(
        db: Session,
        user_id: int,
        organization_id: int,
        unread_only: bool = False,
        notification_type: Optional[NotificationType] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Notification]:
        """Get notifications for a user with filtering"""
        query = db.query(Notification).filter(
            and_(
                Notification.user_id == user_id,
                Notification.organization_id == organization_id,
                or_(
                    Notification.expires_at.is_(None),
                    Notification.expires_at > datetime.utcnow()
                )
            )
        )
        
        if unread_only:
            query = query.filter(Notification.is_read == False)
        
        if notification_type:
            query = query.filter(Notification.notification_type == notification_type)
        
        return query.order_by(Notification.created_at.desc()).limit(limit).offset(offset).all()
    
    @staticmethod
    def mark_as_read(
        db: Session,
        notification_id: int,
        user_id: int
    ) -> Optional[Notification]:
        """Mark notification as read"""
        notification = db.query(Notification).filter(
            and_(
                Notification.id == notification_id,
                Notification.user_id == user_id
            )
        ).first()
        
        if notification and not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            db.commit()
            db.refresh(notification)
        
        return notification
    
    @staticmethod
    def mark_all_as_read(
        db: Session,
        user_id: int,
        organization_id: int
    ) -> int:
        """Mark all notifications as read for a user"""
        count = db.query(Notification).filter(
            and_(
                Notification.user_id == user_id,
                Notification.organization_id == organization_id,
                Notification.is_read == False
            )
        ).update({
            "is_read": True,
            "read_at": datetime.utcnow()
        })
        db.commit()
        return count
    
    @staticmethod
    def delete_notification(
        db: Session,
        notification_id: int,
        user_id: int
    ) -> bool:
        """Delete a notification"""
        notification = db.query(Notification).filter(
            and_(
                Notification.id == notification_id,
                Notification.user_id == user_id
            )
        ).first()
        
        if notification:
            db.delete(notification)
            db.commit()
            return True
        return False
    
    @staticmethod
    def get_unread_count(
        db: Session,
        user_id: int,
        organization_id: int
    ) -> int:
        """Get count of unread notifications"""
        return db.query(Notification).filter(
            and_(
                Notification.user_id == user_id,
                Notification.organization_id == organization_id,
                Notification.is_read == False,
                or_(
                    Notification.expires_at.is_(None),
                    Notification.expires_at > datetime.utcnow()
                )
            )
        ).count()
    
    @staticmethod
    def clean_expired_notifications(db: Session) -> int:
        """Delete expired notifications (maintenance task)"""
        count = db.query(Notification).filter(
            and_(
                Notification.expires_at.isnot(None),
                Notification.expires_at < datetime.utcnow()
            )
        ).delete()
        db.commit()
        return count
    
    @staticmethod
    def get_user_preference(
        db: Session,
        user_id: int,
        organization_id: int,
        event_type: str
    ) -> Optional[NotificationPreference]:
        """Get user's notification preference for an event type"""
        return db.query(NotificationPreference).filter(
            and_(
                NotificationPreference.user_id == user_id,
                NotificationPreference.organization_id == organization_id,
                NotificationPreference.event_type == event_type
            )
        ).first()
    
    @staticmethod
    def update_user_preference(
        db: Session,
        user_id: int,
        organization_id: int,
        event_type: str,
        in_app_enabled: bool = True,
        email_enabled: bool = True,
        digest_enabled: bool = False,
        digest_frequency: Optional[str] = None
    ) -> NotificationPreference:
        """Update or create user notification preference"""
        preference = NotificationService.get_user_preference(
            db, user_id, organization_id, event_type
        )
        
        if preference:
            preference.in_app_enabled = in_app_enabled
            preference.email_enabled = email_enabled
            preference.digest_enabled = digest_enabled
            preference.digest_frequency = digest_frequency
            preference.updated_at = datetime.utcnow()
        else:
            preference = NotificationPreference(
                user_id=user_id,
                organization_id=organization_id,
                event_type=event_type,
                in_app_enabled=in_app_enabled,
                email_enabled=email_enabled,
                digest_enabled=digest_enabled,
                digest_frequency=digest_frequency
            )
            db.add(preference)
        
        db.commit()
        db.refresh(preference)
        return preference


# Convenience functions for common notification types
async def notify_content_published(
    db: Session,
    user_id: int,
    organization_id: int,
    content_title: str,
    content_id: int
):
    """Notify user that content was published"""
    return await NotificationService.create_notification(
        db=db,
        user_id=user_id,
        organization_id=organization_id,
        title="Content Published",
        message=f'Your content "{content_title}" has been published.',
        notification_type=NotificationType.SUCCESS,
        action_url=f"/dashboard/content/{content_id}",
        action_label="View Content",
        meta_data={"content_id": content_id}
    )


async def notify_media_uploaded(
    db: Session,
    user_id: int,
    organization_id: int,
    filename: str,
    media_id: int
):
    """Notify user that media was uploaded"""
    return await NotificationService.create_notification(
        db=db,
        user_id=user_id,
        organization_id=organization_id,
        title="Media Uploaded",
        message=f'File "{filename}" has been uploaded successfully.',
        notification_type=NotificationType.SUCCESS,
        priority=NotificationPriority.LOW,
        action_url=f"/dashboard/media/{media_id}",
        action_label="View Media",
        meta_data={"media_id": media_id}
    )


async def notify_user_invited(
    db: Session,
    user_id: int,
    organization_id: int,
    inviter_name: str,
    organization_name: str
):
    """Notify user they were invited to organization"""
    return await NotificationService.create_notification(
        db=db,
        user_id=user_id,
        organization_id=organization_id,
        title="Organization Invitation",
        message=f"{inviter_name} invited you to join {organization_name}.",
        notification_type=NotificationType.INFO,
        priority=NotificationPriority.HIGH,
        action_url="/dashboard/settings/organizations",
        action_label="View Invitations",
        send_email=True
    )
