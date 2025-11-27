"""
Webhook API endpoints
"""

import secrets
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from backend.api.schemas.webhook import (
    WebhookCreate,
    WebhookDeliveryDetailResponse,
    WebhookDeliveryListResponse,
    WebhookDeliveryResponse,
    WebhookListResponse,
    WebhookResponse,
    WebhookSecretResponse,
    WebhookTestRequest,
    WebhookTestResponse,
    WebhookUpdate,
)
from backend.core.dependencies import get_current_user
from backend.core.rate_limit import get_rate_limit, limiter
from backend.core.webhook_service import WebhookDeliveryService, WebhookEventPublisher
from backend.db.session import get_db
from backend.models.user import User
from backend.models.webhook import Webhook, WebhookDelivery, WebhookEventType, WebhookStatus

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("", response_model=WebhookSecretResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(get_rate_limit())
async def create_webhook(
    request: Request,
    webhook_data: WebhookCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new webhook

    Returns the webhook ID and secret. **Store the secret securely** as it will not be shown again.
    """
    # Generate secure secret
    secret = secrets.token_urlsafe(32)

    # Create webhook
    webhook = Webhook(
        organization_id=current_user.organization_id,
        name=webhook_data.name,
        description=webhook_data.description,
        url=str(webhook_data.url),
        secret=secret,
        events=[event.value for event in webhook_data.events],
        headers=webhook_data.headers,
        max_retries=webhook_data.max_retries,
        retry_delay=webhook_data.retry_delay,
        status=WebhookStatus.ACTIVE,
        is_active=True,
    )

    db.add(webhook)
    db.commit()
    db.refresh(webhook)

    return WebhookSecretResponse(id=webhook.id, secret=secret)


@router.get("", response_model=WebhookListResponse)
@limiter.limit(get_rate_limit())
async def list_webhooks(
    request: Request,
    status_filter: Optional[WebhookStatus] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all webhooks for the organization"""
    # Build query
    query = select(Webhook).where(Webhook.organization_id == current_user.organization_id)

    if status_filter:
        query = query.where(Webhook.status == status_filter)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query)

    # Get webhooks
    query = query.order_by(desc(Webhook.created_at)).offset(skip).limit(limit)
    result = db.execute(query)
    webhooks = result.scalars().all()

    return WebhookListResponse(
        total=total or 0, webhooks=[WebhookResponse.model_validate(wh) for wh in webhooks]
    )


@router.get("/{webhook_id}", response_model=WebhookResponse)
@limiter.limit(get_rate_limit())
async def get_webhook(
    request: Request,
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get webhook details"""
    result = db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id, Webhook.organization_id == current_user.organization_id
        )
    )
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    return WebhookResponse.model_validate(webhook)


@router.patch("/{webhook_id}", response_model=WebhookResponse)
@limiter.limit(get_rate_limit())
async def update_webhook(
    request: Request,
    webhook_id: int,
    webhook_data: WebhookUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update webhook configuration"""
    result = db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id, Webhook.organization_id == current_user.organization_id
        )
    )
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    # Update fields
    update_data = webhook_data.model_dump(exclude_unset=True)

    # Convert events to strings
    if "events" in update_data and update_data["events"]:
        update_data["events"] = [event.value for event in update_data["events"]]

    # Convert URL to string
    if "url" in update_data and update_data["url"]:
        update_data["url"] = str(update_data["url"])

    for field, value in update_data.items():
        setattr(webhook, field, value)

    db.commit()
    db.refresh(webhook)

    return WebhookResponse.model_validate(webhook)


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(get_rate_limit())
async def delete_webhook(
    request: Request,
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a webhook"""
    result = db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id, Webhook.organization_id == current_user.organization_id
        )
    )
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    db.delete(webhook)
    db.commit()


@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
@limiter.limit(get_rate_limit())
async def test_webhook(
    request: Request,
    webhook_id: int,
    test_data: WebhookTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Test webhook by sending a test event

    This creates a test delivery and attempts to send it immediately.
    """
    result = db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id, Webhook.organization_id == current_user.organization_id
        )
    )
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    # Create test payload
    test_payload = test_data.custom_payload or {
        "test": True,
        "message": "This is a test webhook delivery",
    }

    # Publish test event
    delivery_ids = await WebhookEventPublisher.publish(
        test_data.event_type, current_user.organization_id, test_payload, db
    )

    if not delivery_ids:
        return WebhookTestResponse(
            success=False,
            delivery_id=0,
            message="No delivery created - webhook may not be subscribed to this event",
            error="Webhook not subscribed to event type",
        )

    delivery_id = delivery_ids[0]

    # Try to deliver immediately
    try:
        success = await WebhookDeliveryService.deliver_webhook(delivery_id, db)

        # Get delivery details
        result = db.execute(select(WebhookDelivery).where(WebhookDelivery.id == delivery_id))
        delivery = result.scalar_one()

        return WebhookTestResponse(
            success=success,
            delivery_id=delivery_id,
            status_code=delivery.response_status,
            response_body=delivery.response_body[:500] if delivery.response_body else None,
            error=delivery.error_message,
            message="Test delivery completed successfully" if success else "Test delivery failed",
        )

    except Exception as e:
        return WebhookTestResponse(
            success=False,
            delivery_id=delivery_id,
            error=str(e),
            message="Error during test delivery",
        )


@router.post("/{webhook_id}/regenerate-secret", response_model=WebhookSecretResponse)
@limiter.limit(get_rate_limit())
async def regenerate_webhook_secret(
    request: Request,
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Regenerate webhook secret

    **Warning**: This will invalidate the old secret. Update your webhook verification code with the new secret.
    """
    result = db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id, Webhook.organization_id == current_user.organization_id
        )
    )
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    # Generate new secret
    new_secret = secrets.token_urlsafe(32)
    webhook.secret = new_secret

    db.commit()

    return WebhookSecretResponse(
        id=webhook.id,
        secret=new_secret,
        message="Secret regenerated successfully. Update your webhook verification code.",
    )


# Webhook delivery endpoints
@router.get("/{webhook_id}/deliveries", response_model=WebhookDeliveryListResponse)
@limiter.limit(get_rate_limit())
async def list_webhook_deliveries(
    request: Request,
    webhook_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List deliveries for a webhook"""
    # Verify webhook ownership
    result = db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id, Webhook.organization_id == current_user.organization_id
        )
    )
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    # Get total count
    count_query = select(func.count()).where(WebhookDelivery.webhook_id == webhook_id)
    total = db.scalar(count_query)

    # Get deliveries
    query = (
        select(WebhookDelivery)
        .where(WebhookDelivery.webhook_id == webhook_id)
        .order_by(desc(WebhookDelivery.created_at))
        .offset(skip)
        .limit(limit)
    )

    result = db.execute(query)
    deliveries = result.scalars().all()

    return WebhookDeliveryListResponse(
        total=total or 0, deliveries=[WebhookDeliveryResponse.model_validate(d) for d in deliveries]
    )


@router.get("/{webhook_id}/deliveries/{delivery_id}", response_model=WebhookDeliveryDetailResponse)
@limiter.limit(get_rate_limit())
async def get_webhook_delivery(
    request: Request,
    webhook_id: int,
    delivery_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get detailed delivery information"""
    # Verify webhook ownership
    result = db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id, Webhook.organization_id == current_user.organization_id
        )
    )
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    # Get delivery
    result = db.execute(
        select(WebhookDelivery).where(
            WebhookDelivery.id == delivery_id, WebhookDelivery.webhook_id == webhook_id
        )
    )
    delivery = result.scalar_one_or_none()

    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")

    return WebhookDeliveryDetailResponse.model_validate(delivery)


@router.post("/{webhook_id}/deliveries/{delivery_id}/retry", response_model=WebhookTestResponse)
@limiter.limit(get_rate_limit())
async def retry_webhook_delivery(
    request: Request,
    webhook_id: int,
    delivery_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually retry a failed delivery"""
    # Verify webhook ownership
    result = db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id, Webhook.organization_id == current_user.organization_id
        )
    )
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    # Get delivery
    result = db.execute(
        select(WebhookDelivery).where(
            WebhookDelivery.id == delivery_id, WebhookDelivery.webhook_id == webhook_id
        )
    )
    delivery = result.scalar_one_or_none()

    if not delivery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")

    # Attempt delivery
    try:
        success = await WebhookDeliveryService.deliver_webhook(delivery_id, db)

        # Refresh delivery
        db.refresh(delivery)

        return WebhookTestResponse(
            success=success,
            delivery_id=delivery_id,
            status_code=delivery.response_status,
            response_body=delivery.response_body[:500] if delivery.response_body else None,
            error=delivery.error_message,
            message="Retry completed successfully" if success else "Retry failed",
        )

    except Exception as e:
        return WebhookTestResponse(
            success=False, delivery_id=delivery_id, error=str(e), message="Error during retry"
        )


# Event types endpoint
@router.get("/events/types", response_model=List[str])
@limiter.limit(get_rate_limit())
async def list_event_types(request: Request, current_user: User = Depends(get_current_user)):
    """List all available webhook event types"""
    return [event.value for event in WebhookEventType]
