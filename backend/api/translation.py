"""
Translation and Locale Management API endpoints
"""

import json
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend.api.schemas.translation import (
    LocaleCreate,
    LocaleDetectionResponse,
    LocaleResponse,
    LocaleUpdate,
    TranslateRequest,
    TranslateResponse,
    TranslationListResponse,
    TranslationResponse,
    TranslationUpdate,
)
from backend.core.dependencies import get_current_user
from backend.core.rate_limit import get_rate_limit, limiter
from backend.core.translation_service import get_translation_service
from backend.db.session import get_db
from backend.models.content import ContentEntry, ContentType
from backend.models.translation import Locale, Translation
from backend.models.user import User

router = APIRouter(prefix="/translation", tags=["Translation & Localization"])


# Locale Endpoints


@router.post("/locales", response_model=LocaleResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(get_rate_limit())
async def create_locale(
    request: Request,
    locale_data: LocaleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new locale for the organization
    """
    # Check if locale code already exists for this organization
    existing = (
        db.query(Locale)
        .filter(
            Locale.organization_id == current_user.organization_id, Locale.code == locale_data.code
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Locale with code '{locale_data.code}' already exists",
        )

    # If this is set as default, unset other defaults
    if locale_data.is_default:
        db.query(Locale).filter(
            Locale.organization_id == current_user.organization_id, Locale.is_default == True
        ).update({"is_default": False})

    locale = Locale(
        organization_id=current_user.organization_id,
        code=locale_data.code,
        name=locale_data.name,
        native_name=locale_data.native_name,
        is_default=locale_data.is_default,
        is_enabled=locale_data.is_enabled,
        auto_translate=locale_data.auto_translate,
    )

    db.add(locale)
    db.commit()
    db.refresh(locale)

    return locale


@router.get("/locales", response_model=List[LocaleResponse])
@limiter.limit(get_rate_limit())
async def list_locales(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    enabled_only: bool = Query(False, description="Show only enabled locales"),
):
    """
    List all locales for the organization
    """
    query = db.query(Locale).filter(Locale.organization_id == current_user.organization_id)

    if enabled_only:
        query = query.filter(Locale.is_enabled == True)

    locales = query.order_by(Locale.is_default.desc(), Locale.name).all()
    return locales


@router.get("/locales/{locale_id}", response_model=LocaleResponse)
@limiter.limit(get_rate_limit())
async def get_locale(
    request: Request,
    locale_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific locale by ID
    """
    locale = (
        db.query(Locale)
        .filter(Locale.id == locale_id, Locale.organization_id == current_user.organization_id)
        .first()
    )

    if not locale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Locale not found")

    return locale


@router.put("/locales/{locale_id}", response_model=LocaleResponse)
@limiter.limit(get_rate_limit())
async def update_locale(
    request: Request,
    locale_id: UUID,
    locale_data: LocaleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a locale
    """
    locale = (
        db.query(Locale)
        .filter(Locale.id == locale_id, Locale.organization_id == current_user.organization_id)
        .first()
    )

    if not locale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Locale not found")

    # If setting as default, unset other defaults
    if locale_data.is_default and not locale.is_default:
        db.query(Locale).filter(
            Locale.organization_id == current_user.organization_id, Locale.is_default == True
        ).update({"is_default": False})

    # Update fields
    if locale_data.name is not None:
        locale.name = locale_data.name
    if locale_data.native_name is not None:
        locale.native_name = locale_data.native_name
    if locale_data.is_default is not None:
        locale.is_default = locale_data.is_default
    if locale_data.is_enabled is not None:
        locale.is_enabled = locale_data.is_enabled
    if locale_data.auto_translate is not None:
        locale.auto_translate = locale_data.auto_translate

    db.commit()
    db.refresh(locale)

    return locale


@router.delete("/locales/{locale_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(get_rate_limit())
async def delete_locale(
    request: Request,
    locale_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a locale (cascades to translations)
    """
    locale = (
        db.query(Locale)
        .filter(Locale.id == locale_id, Locale.organization_id == current_user.organization_id)
        .first()
    )

    if not locale:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Locale not found")

    if locale.is_default:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete the default locale"
        )

    db.delete(locale)
    db.commit()


# Translation Endpoints


def translate_content_entry_background(
    entry_id: UUID,
    locale_ids: List[int],
    force_retranslate: bool,
    organization_id: UUID,
    db: Session,
):
    """Background task to translate content entry"""
    translation_service = get_translation_service()

    # Get content entry
    entry = (
        db.query(ContentEntry)
        .join(ContentType)
        .filter(ContentEntry.id == entry_id, ContentType.organization_id == organization_id)
        .first()
    )

    if not entry:
        return

    # Parse entry data
    entry_data = json.loads(entry.data) if entry.data else {}

    # Get locales
    locales = (
        db.query(Locale)
        .filter(
            Locale.id.in_(locale_ids),
            Locale.organization_id == organization_id,
            Locale.is_enabled == True,
        )
        .all()
    )

    for locale in locales:
        # Check if translation exists
        existing_translation = (
            db.query(Translation)
            .filter(Translation.content_entry_id == entry_id, Translation.locale_id == locale.id)
            .first()
        )

        if existing_translation and not force_retranslate:
            continue

        # Translate the content
        translated_data = translation_service.translate_dict(
            entry_data,
            target_lang=locale.code.split("-")[0],  # Use base language code
            source_lang=None,
        )

        if existing_translation:
            # Update existing
            existing_translation.translated_data = json.dumps(translated_data)
            existing_translation.status = "completed"
            existing_translation.translation_service = "google"
            existing_translation.version += 1
        else:
            # Create new translation
            translation = Translation(
                content_entry_id=entry_id,
                locale_id=locale.id,
                translated_data=json.dumps(translated_data),
                status="completed",
                translation_service="google",
                quality_score=0.95,
            )
            db.add(translation)

    db.commit()


@router.post("/translate", response_model=TranslateResponse)
@limiter.limit(get_rate_limit())
async def translate_content(
    request: Request,
    translate_req: TranslateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Translate a content entry to multiple locales
    """
    # Verify content entry exists and belongs to organization
    entry = (
        db.query(ContentEntry)
        .join(ContentType)
        .filter(
            ContentEntry.id == translate_req.content_entry_id,
            ContentType.organization_id == current_user.organization_id,
        )
        .first()
    )

    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content entry not found")

    # Verify locales exist
    locales = (
        db.query(Locale)
        .filter(
            Locale.id.in_(translate_req.target_locale_ids),
            Locale.organization_id == current_user.organization_id,
        )
        .all()
    )

    if len(locales) != len(translate_req.target_locale_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="One or more locale IDs are invalid"
        )

    # Queue translation as background task
    background_tasks.add_task(
        translate_content_entry_background,
        translate_req.content_entry_id,
        translate_req.target_locale_ids,
        translate_req.force_retranslate,
        current_user.organization_id,
        db,
    )

    # Return immediate response
    return TranslateResponse(
        content_entry_id=translate_req.content_entry_id,
        translations=[],
        message=f"Translation queued for {len(locales)} locale(s)",
    )


@router.get("/translations", response_model=TranslationListResponse)
@limiter.limit(get_rate_limit())
async def list_translations(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    content_entry_id: Optional[UUID] = Query(None),
    locale_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    """
    List translations with pagination and filters
    """
    query = (
        db.query(Translation)
        .join(ContentEntry)
        .join(ContentType)
        .filter(ContentType.organization_id == current_user.organization_id)
    )

    if content_entry_id:
        query = query.filter(Translation.content_entry_id == content_entry_id)

    if locale_id:
        query = query.filter(Translation.locale_id == locale_id)

    if status:
        query = query.filter(Translation.status == status)

    total = query.count()
    translations = query.offset((page - 1) * page_size).limit(page_size).all()

    # Parse translated_data for each translation
    items = []
    for translation in translations:
        translated_data = (
            json.loads(translation.translated_data) if translation.translated_data else {}
        )
        items.append(
            TranslationResponse(
                id=translation.id,
                content_entry_id=translation.content_entry_id,
                locale_id=translation.locale_id,
                translated_data=translated_data,
                status=translation.status,
                source_locale=translation.source_locale,
                translation_service=translation.translation_service,
                quality_score=translation.quality_score,
                is_manual=translation.is_manual,
                version=translation.version,
                created_at=translation.created_at,
                updated_at=translation.updated_at,
            )
        )

    return TranslationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/translations/{translation_id}", response_model=TranslationResponse)
@limiter.limit(get_rate_limit())
async def get_translation(
    request: Request,
    translation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific translation by ID
    """
    translation = (
        db.query(Translation)
        .join(ContentEntry)
        .join(ContentType)
        .filter(
            Translation.id == translation_id,
            ContentType.organization_id == current_user.organization_id,
        )
        .first()
    )

    if not translation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Translation not found")

    translated_data = json.loads(translation.translated_data) if translation.translated_data else {}

    return TranslationResponse(
        id=translation.id,
        content_entry_id=translation.content_entry_id,
        locale_id=translation.locale_id,
        translated_data=translated_data,
        status=translation.status,
        source_locale=translation.source_locale,
        translation_service=translation.translation_service,
        quality_score=translation.quality_score,
        is_manual=translation.is_manual,
        version=translation.version,
        created_at=translation.created_at,
        updated_at=translation.updated_at,
    )


@router.put("/translations/{translation_id}", response_model=TranslationResponse)
@limiter.limit(get_rate_limit())
async def update_translation(
    request: Request,
    translation_id: UUID,
    translation_data: TranslationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a translation (for manual overrides)
    """
    translation = (
        db.query(Translation)
        .join(ContentEntry)
        .join(ContentType)
        .filter(
            Translation.id == translation_id,
            ContentType.organization_id == current_user.organization_id,
        )
        .first()
    )

    if not translation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Translation not found")

    # Update fields
    if translation_data.translated_data is not None:
        translation.translated_data = json.dumps(translation_data.translated_data)
        translation.version += 1
    if translation_data.status is not None:
        translation.status = translation_data.status
    if translation_data.quality_score is not None:
        translation.quality_score = translation_data.quality_score
    if translation_data.is_manual is not None:
        translation.is_manual = translation_data.is_manual

    db.commit()
    db.refresh(translation)

    translated_data = json.loads(translation.translated_data) if translation.translated_data else {}

    return TranslationResponse(
        id=translation.id,
        content_entry_id=translation.content_entry_id,
        locale_id=translation.locale_id,
        translated_data=translated_data,
        status=translation.status,
        source_locale=translation.source_locale,
        translation_service=translation.translation_service,
        quality_score=translation.quality_score,
        is_manual=translation.is_manual,
        version=translation.version,
        created_at=translation.created_at,
        updated_at=translation.updated_at,
    )


@router.delete("/translations/{translation_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(get_rate_limit())
async def delete_translation(
    request: Request,
    translation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a translation
    """
    translation = (
        db.query(Translation)
        .join(ContentEntry)
        .join(ContentType)
        .filter(
            Translation.id == translation_id,
            ContentType.organization_id == current_user.organization_id,
        )
        .first()
    )

    if not translation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Translation not found")

    db.delete(translation)
    db.commit()


# Locale Detection


@router.post("/detect-locale", response_model=LocaleDetectionResponse)
@limiter.limit(get_rate_limit())
async def detect_locale(
    request: Request,
    text: str = Query(..., description="Text to detect language from"),
    current_user: User = Depends(get_current_user),
):
    """
    Detect language from text
    """
    translation_service = get_translation_service()
    lang_code, confidence = translation_service.detect_language(text)

    return LocaleDetectionResponse(
        detected_locale=lang_code,
        confidence=confidence,
        fallback_chain=[lang_code, "en"],
        source="text_analysis",
    )
