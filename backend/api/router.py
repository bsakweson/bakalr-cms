"""
API Router aggregating all endpoints
"""

from fastapi import APIRouter

from backend.api import (
    analytics,
    api_keys,
    audit_logs,
    auth,
    content,
    content_template,
    delivery,
    devices,
    field_permissions,
    media,
    metrics,
    notifications,
    oauth2,
    organization,
    password_reset,
    preview,
    relationship,
    roles,
    schedule,
    search,
    seo,
    sessions,
    social_login,
    tenant,
    theme,
    translation,
    two_factor,
    users,
    webhook,
)

api_router = APIRouter()

# Include routers
api_router.include_router(analytics.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(roles.router)
api_router.include_router(organization.router)
api_router.include_router(audit_logs.router)
api_router.include_router(two_factor.router)
api_router.include_router(password_reset.router)
api_router.include_router(api_keys.router)
api_router.include_router(tenant.router)
api_router.include_router(devices.router)
api_router.include_router(sessions.router)
api_router.include_router(social_login.router)
api_router.include_router(oauth2.router)
api_router.include_router(content.router)
api_router.include_router(translation.router)
api_router.include_router(seo.router)
api_router.include_router(media.router)
api_router.include_router(webhook.router)
api_router.include_router(preview.router)
api_router.include_router(delivery.router)
api_router.include_router(schedule.router)
api_router.include_router(relationship.router)
api_router.include_router(field_permissions.router)
api_router.include_router(theme.router)
api_router.include_router(content_template.router)
api_router.include_router(notifications.router)
api_router.include_router(search.router)
api_router.include_router(metrics.router)


@api_router.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Welcome to Bakalr CMS API",
        "version": "0.1.0",
        "docs": "/api/docs",
    }
