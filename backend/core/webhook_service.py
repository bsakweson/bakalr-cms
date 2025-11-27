"""
Webhook event system for publishing and delivering events
"""
import uuid
import hmac
import hashlib
import httpx
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.webhook import (
    Webhook, WebhookDelivery, WebhookStatus, 
    WebhookEventType, WebhookDeliveryStatus
)


class WebhookEventPublisher:
    """
    Event publisher for webhook system
    Publishes events to subscribed webhooks
    """
    
    @staticmethod
    async def publish(
        event_type: WebhookEventType,
        organization_id: int,
        data: Dict[str, Any],
        db: AsyncSession
    ) -> List[int]:
        """
        Publish an event to all subscribed webhooks
        
        Args:
            event_type: Type of event
            organization_id: Organization ID
            data: Event data
            db: Database session
            
        Returns:
            List of delivery IDs created
        """
        # Find active webhooks subscribed to this event
        result = await db.execute(
            select(Webhook).where(
                Webhook.organization_id == organization_id,
                Webhook.is_active == True,
                Webhook.status == WebhookStatus.ACTIVE
            )
        )
        webhooks = result.scalars().all()
        
        # Filter webhooks subscribed to this event type
        subscribed_webhooks = [
            wh for wh in webhooks 
            if event_type.value in wh.events
        ]
        
        if not subscribed_webhooks:
            return []
        
        # Create event payload
        event_id = f"evt_{uuid.uuid4().hex}"
        payload = {
            "event_id": event_id,
            "event_type": event_type.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "organization_id": organization_id,
            "data": data
        }
        
        # Create delivery records
        delivery_ids = []
        for webhook in subscribed_webhooks:
            delivery = WebhookDelivery(
                webhook_id=webhook.id,
                event_type=event_type.value,
                event_id=event_id,
                payload=payload,
                status=WebhookDeliveryStatus.PENDING,
                max_attempts=webhook.max_retries + 1  # +1 for initial attempt
            )
            db.add(delivery)
            await db.flush()
            delivery_ids.append(delivery.id)
            
            # Update webhook last_triggered_at
            webhook.last_triggered_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        # Schedule deliveries asynchronously (non-blocking)
        asyncio.create_task(
            WebhookDeliveryService.deliver_pending(delivery_ids)
        )
        
        return delivery_ids


class WebhookDeliveryService:
    """
    Service for delivering webhooks with retry logic
    """
    
    @staticmethod
    def generate_signature(payload: str, secret: str) -> str:
        """
        Generate HMAC-SHA256 signature for webhook payload
        
        Args:
            payload: JSON payload string
            secret: Webhook secret
            
        Returns:
            Hex digest of signature
        """
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
    
    @staticmethod
    async def deliver_webhook(
        delivery_id: int,
        db: AsyncSession = None
    ) -> bool:
        """
        Deliver a single webhook
        
        Args:
            delivery_id: Delivery ID
            db: Database session (optional, will create if not provided)
            
        Returns:
            True if delivery successful, False otherwise
        """
        if db is None:
            async for session in get_async_session():
                return await WebhookDeliveryService.deliver_webhook(delivery_id, session)
        
        # Get delivery and webhook
        result = await db.execute(
            select(WebhookDelivery).where(WebhookDelivery.id == delivery_id)
        )
        delivery = result.scalar_one_or_none()
        
        if not delivery:
            return False
        
        result = await db.execute(
            select(Webhook).where(Webhook.id == delivery.webhook_id)
        )
        webhook = result.scalar_one_or_none()
        
        if not webhook or not webhook.is_active:
            delivery.status = WebhookDeliveryStatus.FAILED
            delivery.error_message = "Webhook inactive or not found"
            await db.commit()
            return False
        
        # Update delivery status
        delivery.status = WebhookDeliveryStatus.DELIVERING
        delivery.attempt_count += 1
        if delivery.attempt_count == 1:
            delivery.first_attempted_at = datetime.now(timezone.utc)
        delivery.last_attempted_at = datetime.now(timezone.utc)
        await db.commit()
        
        # Prepare request
        import json
        payload_json = json.dumps(delivery.payload, separators=(',', ':'))
        signature = WebhookDeliveryService.generate_signature(payload_json, webhook.secret)
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Bakalr-CMS-Webhook/1.0",
            "X-Webhook-Signature": f"sha256={signature}",
            "X-Webhook-ID": str(webhook.id),
            "X-Event-Type": delivery.event_type,
            "X-Event-ID": delivery.event_id,
            "X-Delivery-ID": str(delivery.id),
            "X-Delivery-Attempt": str(delivery.attempt_count)
        }
        
        # Add custom headers
        if webhook.headers:
            headers.update(webhook.headers)
        
        # Deliver webhook
        success = False
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    webhook.url,
                    content=payload_json,
                    headers=headers
                )
                
                # Record response
                delivery.response_status = response.status_code
                delivery.response_body = response.text[:5000]  # Limit size
                delivery.response_headers = dict(response.headers)
                
                # Check if successful (2xx status code)
                if 200 <= response.status_code < 300:
                    delivery.status = WebhookDeliveryStatus.SUCCESS
                    delivery.completed_at = datetime.now(timezone.utc)
                    webhook.success_count += 1
                    webhook.last_success_at = datetime.now(timezone.utc)
                    success = True
                else:
                    delivery.error_message = f"HTTP {response.status_code}: {response.text[:200]}"
                    success = False
        
        except httpx.TimeoutException as e:
            delivery.error_message = f"Timeout: {str(e)}"
            success = False
        
        except httpx.RequestError as e:
            delivery.error_message = f"Request error: {str(e)}"
            success = False
        
        except Exception as e:
            delivery.error_message = f"Unexpected error: {str(e)}"
            success = False
        
        # Handle failure
        if not success:
            if delivery.attempt_count < delivery.max_attempts:
                # Schedule retry
                delivery.status = WebhookDeliveryStatus.RETRYING
                # Exponential backoff: 60s, 120s, 240s, etc.
                delay = webhook.retry_delay * (2 ** (delivery.attempt_count - 1))
                delivery.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
            else:
                # Max retries reached
                delivery.status = WebhookDeliveryStatus.FAILED
                delivery.completed_at = datetime.now(timezone.utc)
                webhook.failure_count += 1
                webhook.last_failure_at = datetime.now(timezone.utc)
        
        await db.commit()
        return success
    
    @staticmethod
    async def deliver_pending(delivery_ids: List[int]) -> None:
        """
        Deliver multiple pending webhooks
        
        Args:
            delivery_ids: List of delivery IDs
        """
        async for db in get_async_session():
            for delivery_id in delivery_ids:
                try:
                    await WebhookDeliveryService.deliver_webhook(delivery_id, db)
                except Exception as e:
                    print(f"Error delivering webhook {delivery_id}: {e}")
    
    @staticmethod
    async def retry_failed_deliveries(db: AsyncSession) -> int:
        """
        Retry failed deliveries that are due for retry
        
        Args:
            db: Database session
            
        Returns:
            Number of deliveries retried
        """
        # Find deliveries due for retry
        result = await db.execute(
            select(WebhookDelivery).where(
                WebhookDelivery.status == WebhookDeliveryStatus.RETRYING,
                WebhookDelivery.next_retry_at <= datetime.now(timezone.utc)
            ).limit(100)  # Process in batches
        )
        deliveries = result.scalars().all()
        
        count = 0
        for delivery in deliveries:
            try:
                await WebhookDeliveryService.deliver_webhook(delivery.id, db)
                count += 1
            except Exception as e:
                print(f"Error retrying delivery {delivery.id}: {e}")
        
        return count


# Convenience functions for publishing events (async)
async def publish_content_created(content_id: int, organization_id: int, data: Dict[str, Any], db: AsyncSession):
    """Publish content.created event"""
    await WebhookEventPublisher.publish(
        WebhookEventType.CONTENT_CREATED,
        organization_id,
        {"content_id": content_id, **data},
        db
    )


async def publish_content_updated(content_id: int, organization_id: int, data: Dict[str, Any], db: AsyncSession):
    """Publish content.updated event"""
    await WebhookEventPublisher.publish(
        WebhookEventType.CONTENT_UPDATED,
        organization_id,
        {"content_id": content_id, **data},
        db
    )


async def publish_content_deleted(content_id: int, organization_id: int, data: Dict[str, Any], db: AsyncSession):
    """Publish content.deleted event"""
    await WebhookEventPublisher.publish(
        WebhookEventType.CONTENT_DELETED,
        organization_id,
        {"content_id": content_id, **data},
        db
    )


async def publish_content_published(content_id: int, organization_id: int, data: Dict[str, Any], db: AsyncSession):
    """Publish content.published event"""
    await WebhookEventPublisher.publish(
        WebhookEventType.CONTENT_PUBLISHED,
        organization_id,
        {"content_id": content_id, **data},
        db
    )


async def publish_media_uploaded(media_id: int, organization_id: int, data: Dict[str, Any], db: AsyncSession):
    """Publish media.uploaded event"""
    await WebhookEventPublisher.publish(
        WebhookEventType.MEDIA_UPLOADED,
        organization_id,
        {"media_id": media_id, **data},
        db
    )


async def publish_media_deleted(media_id: int, organization_id: int, data: Dict[str, Any], db: AsyncSession):
    """Publish media.deleted event"""
    await WebhookEventPublisher.publish(
        WebhookEventType.MEDIA_DELETED,
        organization_id,
        {"media_id": media_id, **data},
        db
    )


# Sync wrappers for background tasks (work with sync DB sessions)
def publish_content_created_sync(content_id: int, organization_id: int, db: Session):
    """Publish content.created event (sync wrapper)"""
    # For sync sessions, we just skip webhook publishing
    # In production, you'd queue this for async processing
    pass


def publish_content_updated_sync(content_id: int, organization_id: int, db: Session):
    """Publish content.updated event (sync wrapper)"""
    pass


def publish_content_deleted_sync(content_id: int, organization_id: int, db: Session):
    """Publish content.deleted event (sync wrapper)"""
    pass


def publish_content_published_sync(content_id: int, organization_id: int, db: Session):
    """Publish content.published event (sync wrapper)"""
    pass


def publish_media_uploaded_sync(media_id: int, organization_id: int, db: Session):
    """Publish media.uploaded event (sync wrapper)"""
    pass


def publish_media_deleted_sync(media_id: int, organization_id: int, db: Session):
    """Publish media.deleted event (sync wrapper)"""
    pass

