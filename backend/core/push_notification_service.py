"""
Push Notification Service - Send notifications via FCM, APNS, Gotify, and Ntfy.
Supports multiple providers with automatic fallback and device targeting.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.device import Device, DevicePlatform, DeviceStatus


class PushProvider(str, Enum):
    """Supported push notification providers"""

    FCM = "fcm"  # Firebase Cloud Messaging (Android/Web)
    APNS = "apns"  # Apple Push Notification Service (iOS)
    GOTIFY = "gotify"  # Self-hosted Gotify server
    NTFY = "ntfy"  # Self-hosted or public ntfy.sh
    WEB_PUSH = "web_push"  # Web Push API


class NotificationPriority(str, Enum):
    """Notification priority levels"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class PushNotification:
    """Push notification data structure"""

    def __init__(
        self,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        image_url: Optional[str] = None,
        action_url: Optional[str] = None,
        badge_count: Optional[int] = None,
        sound: Optional[str] = None,
        ttl: int = 86400,  # 24 hours default
    ):
        self.title = title
        self.body = body
        self.data = data or {}
        self.priority = priority
        self.image_url = image_url
        self.action_url = action_url
        self.badge_count = badge_count
        self.sound = sound
        self.ttl = ttl
        self.sent_at = datetime.now(timezone.utc)


class PushProviderBase(ABC):
    """Abstract base class for push notification providers"""

    @abstractmethod
    async def send(
        self,
        token: str,
        notification: PushNotification,
    ) -> Dict[str, Any]:
        """Send notification to a single token"""
        pass

    @abstractmethod
    async def send_batch(
        self,
        tokens: List[str],
        notification: PushNotification,
    ) -> Dict[str, Any]:
        """Send notification to multiple tokens"""
        pass


class FCMProvider(PushProviderBase):
    """Firebase Cloud Messaging provider"""

    def __init__(self):
        self.api_key = getattr(settings, "FCM_API_KEY", None)
        self.project_id = getattr(settings, "FCM_PROJECT_ID", None)
        self.api_url = f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"

    async def send(self, token: str, notification: PushNotification) -> Dict[str, Any]:
        if not self.api_key:
            return {"success": False, "error": "FCM not configured"}

        message = {
            "message": {
                "token": token,
                "notification": {
                    "title": notification.title,
                    "body": notification.body,
                },
                "data": {k: str(v) for k, v in notification.data.items()},
                "android": {
                    "priority": (
                        "high"
                        if notification.priority
                        in [NotificationPriority.HIGH, NotificationPriority.URGENT]
                        else "normal"
                    ),
                    "ttl": f"{notification.ttl}s",
                },
            }
        }

        if notification.image_url:
            message["message"]["notification"]["image"] = notification.image_url

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=message,
                timeout=30.0,
            )

            if response.status_code == 200:
                return {"success": True, "response": response.json()}
            else:
                return {"success": False, "error": response.text, "status": response.status_code}

    async def send_batch(self, tokens: List[str], notification: PushNotification) -> Dict[str, Any]:
        results = []
        for token in tokens:
            result = await self.send(token, notification)
            results.append({"token": token, **result})

        success_count = sum(1 for r in results if r.get("success"))
        return {
            "success": success_count > 0,
            "total": len(tokens),
            "sent": success_count,
            "failed": len(tokens) - success_count,
            "results": results,
        }


class APNSProvider(PushProviderBase):
    """Apple Push Notification Service provider"""

    def __init__(self):
        self.key_id = getattr(settings, "APNS_KEY_ID", None)
        self.team_id = getattr(settings, "APNS_TEAM_ID", None)
        self.bundle_id = getattr(settings, "APNS_BUNDLE_ID", None)
        self.is_production = getattr(settings, "APNS_PRODUCTION", False)

        if self.is_production:
            self.api_url = "https://api.push.apple.com/3/device"
        else:
            self.api_url = "https://api.sandbox.push.apple.com/3/device"

    async def send(self, token: str, notification: PushNotification) -> Dict[str, Any]:
        if not all([self.key_id, self.team_id, self.bundle_id]):
            return {"success": False, "error": "APNS not configured"}

        payload = {
            "aps": {
                "alert": {
                    "title": notification.title,
                    "body": notification.body,
                },
                "sound": notification.sound or "default",
            }
        }

        if notification.badge_count is not None:
            payload["aps"]["badge"] = notification.badge_count

        if notification.data:
            payload.update(notification.data)

        # Note: Full APNS implementation requires JWT signing with private key
        # This is a simplified version - production would use PyAPNs2 library
        return {"success": False, "error": "APNS requires additional setup (JWT signing)"}

    async def send_batch(self, tokens: List[str], notification: PushNotification) -> Dict[str, Any]:
        results = []
        for token in tokens:
            result = await self.send(token, notification)
            results.append({"token": token, **result})

        success_count = sum(1 for r in results if r.get("success"))
        return {
            "success": success_count > 0,
            "total": len(tokens),
            "sent": success_count,
            "failed": len(tokens) - success_count,
            "results": results,
        }


class GotifyProvider(PushProviderBase):
    """Gotify self-hosted push notification provider"""

    def __init__(self):
        self.server_url = getattr(settings, "GOTIFY_SERVER_URL", None)
        self.app_token = getattr(settings, "GOTIFY_APP_TOKEN", None)

    async def send(self, token: str, notification: PushNotification) -> Dict[str, Any]:
        if not self.server_url or not self.app_token:
            return {"success": False, "error": "Gotify not configured"}

        # Gotify uses client tokens, not device tokens
        # The token parameter here would be the client's Gotify token
        priority_map = {
            NotificationPriority.LOW: 1,
            NotificationPriority.NORMAL: 5,
            NotificationPriority.HIGH: 8,
            NotificationPriority.URGENT: 10,
        }

        message = {
            "title": notification.title,
            "message": notification.body,
            "priority": priority_map.get(notification.priority, 5),
        }

        if notification.action_url:
            message["extras"] = {
                "client::notification": {"click": {"url": notification.action_url}}
            }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.server_url}/message",
                headers={
                    "X-Gotify-Key": self.app_token,
                    "Content-Type": "application/json",
                },
                json=message,
                timeout=30.0,
            )

            if response.status_code == 200:
                return {"success": True, "response": response.json()}
            else:
                return {"success": False, "error": response.text, "status": response.status_code}

    async def send_batch(self, tokens: List[str], notification: PushNotification) -> Dict[str, Any]:
        # Gotify broadcasts to all clients - send once
        result = await self.send("broadcast", notification)
        return {
            "success": result.get("success", False),
            "total": len(tokens),
            "sent": len(tokens) if result.get("success") else 0,
            "failed": 0 if result.get("success") else len(tokens),
            "results": [result],
        }


class NtfyProvider(PushProviderBase):
    """Ntfy push notification provider (self-hosted or ntfy.sh)"""

    def __init__(self):
        self.server_url = getattr(settings, "NTFY_SERVER_URL", "https://ntfy.sh")
        self.default_topic = getattr(settings, "NTFY_DEFAULT_TOPIC", None)
        self.access_token = getattr(settings, "NTFY_ACCESS_TOKEN", None)

    async def send(self, token: str, notification: PushNotification) -> Dict[str, Any]:
        # Token is the ntfy topic for the user/device
        topic = token or self.default_topic
        if not topic:
            return {"success": False, "error": "No ntfy topic specified"}

        priority_map = {
            NotificationPriority.LOW: "min",
            NotificationPriority.NORMAL: "default",
            NotificationPriority.HIGH: "high",
            NotificationPriority.URGENT: "urgent",
        }

        headers = {
            "Title": notification.title,
            "Priority": priority_map.get(notification.priority, "default"),
            "Tags": "bell",
        }

        if notification.action_url:
            headers["Click"] = notification.action_url

        if notification.image_url:
            headers["Attach"] = notification.image_url

        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.server_url}/{topic}",
                headers=headers,
                content=notification.body,
                timeout=30.0,
            )

            if response.status_code in [200, 204]:
                return {"success": True, "topic": topic}
            else:
                return {"success": False, "error": response.text, "status": response.status_code}

    async def send_batch(self, tokens: List[str], notification: PushNotification) -> Dict[str, Any]:
        results = []
        for token in tokens:
            result = await self.send(token, notification)
            results.append({"token": token, **result})

        success_count = sum(1 for r in results if r.get("success"))
        return {
            "success": success_count > 0,
            "total": len(tokens),
            "sent": success_count,
            "failed": len(tokens) - success_count,
            "results": results,
        }


class PushNotificationService:
    """
    Main push notification service with multi-provider support.
    Automatically selects the appropriate provider based on device platform.
    """

    def __init__(self, db: Session):
        self.db = db
        self.providers: Dict[PushProvider, PushProviderBase] = {
            PushProvider.FCM: FCMProvider(),
            PushProvider.APNS: APNSProvider(),
            PushProvider.GOTIFY: GotifyProvider(),
            PushProvider.NTFY: NtfyProvider(),
        }

    def _get_provider_for_device(self, device: Device) -> Optional[PushProviderBase]:
        """Get the appropriate provider for a device"""
        if device.push_provider:
            provider_enum = PushProvider(device.push_provider)
            return self.providers.get(provider_enum)

        # Auto-select based on platform
        if device.platform == DevicePlatform.IOS:
            return self.providers[PushProvider.APNS]
        elif device.platform in [DevicePlatform.ANDROID, DevicePlatform.WEB]:
            return self.providers[PushProvider.FCM]
        else:
            # Default to ntfy for desktop/other
            return self.providers[PushProvider.NTFY]

    async def send_to_device(
        self,
        device: Device,
        notification: PushNotification,
    ) -> Dict[str, Any]:
        """Send notification to a single device"""
        if device.status != DeviceStatus.ACTIVE:
            return {"success": False, "error": f"Device is {device.status}"}

        if not device.push_token:
            return {"success": False, "error": "Device has no push token"}

        provider = self._get_provider_for_device(device)
        if not provider:
            return {"success": False, "error": "No provider available for device"}

        result = await provider.send(device.push_token, notification)

        # Update device push stats
        if result.get("success"):
            device.last_push_at = datetime.now(timezone.utc)

        return result

    async def send_to_user(
        self,
        user_id: str,
        notification: PushNotification,
        platforms: Optional[List[DevicePlatform]] = None,
    ) -> Dict[str, Any]:
        """Send notification to all of a user's devices"""
        query = self.db.query(Device).filter(
            Device.user_id == user_id,
            Device.status == DeviceStatus.ACTIVE,
            Device.push_token.isnot(None),
        )

        if platforms:
            query = query.filter(Device.platform.in_(platforms))

        devices = query.all()

        if not devices:
            return {"success": False, "error": "No active devices with push tokens"}

        results = []
        for device in devices:
            result = await self.send_to_device(device, notification)
            results.append(
                {
                    "device_id": str(device.id),
                    "device_name": device.display_name,
                    "platform": device.platform.value,
                    **result,
                }
            )

        success_count = sum(1 for r in results if r.get("success"))
        return {
            "success": success_count > 0,
            "total": len(devices),
            "sent": success_count,
            "failed": len(devices) - success_count,
            "results": results,
        }

    async def send_to_organization(
        self,
        organization_id: int,
        notification: PushNotification,
        user_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Send notification to all users in an organization"""
        from backend.models.user import User

        query = (
            self.db.query(Device)
            .join(User)
            .filter(
                User.organization_id == organization_id,
                Device.status == DeviceStatus.ACTIVE,
                Device.push_token.isnot(None),
            )
        )

        if user_ids:
            query = query.filter(Device.user_id.in_(user_ids))

        devices = query.all()

        if not devices:
            return {"success": False, "error": "No active devices with push tokens"}

        # Group by provider for batch sending
        provider_tokens: Dict[PushProvider, List[tuple]] = {}
        for device in devices:
            provider = self._get_provider_for_device(device)
            if provider:
                provider_type = next(
                    (k for k, v in self.providers.items() if v == provider), PushProvider.NTFY
                )
                if provider_type not in provider_tokens:
                    provider_tokens[provider_type] = []
                provider_tokens[provider_type].append((device, device.push_token))

        results = []
        for provider_type, device_tokens in provider_tokens.items():
            provider = self.providers[provider_type]
            tokens = [t[1] for t in device_tokens]
            batch_result = await provider.send_batch(tokens, notification)

            # Map results back to devices
            for i, (device, _) in enumerate(device_tokens):
                device_result = (
                    batch_result.get("results", [{}])[i]
                    if i < len(batch_result.get("results", []))
                    else {}
                )
                results.append(
                    {
                        "device_id": str(device.id),
                        "device_name": device.display_name,
                        "provider": provider_type.value,
                        **device_result,
                    }
                )

        success_count = sum(1 for r in results if r.get("success"))
        return {
            "success": success_count > 0,
            "total": len(devices),
            "sent": success_count,
            "failed": len(devices) - success_count,
            "results": results,
        }

    async def send_security_alert(
        self,
        user_id: str,
        alert_type: str,
        details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Send security alert notification"""
        alert_titles = {
            "new_login": "New Login Detected",
            "password_changed": "Password Changed",
            "device_added": "New Device Added",
            "suspicious_activity": "Suspicious Activity Detected",
            "2fa_disabled": "Two-Factor Authentication Disabled",
        }

        notification = PushNotification(
            title=alert_titles.get(alert_type, "Security Alert"),
            body=details.get("message", "A security event occurred on your account."),
            data={"alert_type": alert_type, **details},
            priority=NotificationPriority.HIGH,
            action_url=details.get("action_url"),
        )

        return await self.send_to_user(user_id, notification)


def get_push_notification_service(db: Session) -> PushNotificationService:
    """Factory function to create PushNotificationService"""
    return PushNotificationService(db)
