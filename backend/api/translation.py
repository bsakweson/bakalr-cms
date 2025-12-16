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
from backend.core.dependencies import get_current_user, get_current_user_flexible
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
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
    enabled_only: bool = Query(False, description="Show only enabled locales"),
):
    """
    List all locales for the organization.
    Supports both JWT and API key authentication.
    """
    query = db.query(Locale).filter(Locale.organization_id == current_user.organization_id)

    if enabled_only:
        query = query.filter(Locale.is_enabled == True)

    locales = query.order_by(Locale.is_default.desc(), Locale.name).all()
    return locales


@router.get("/locales/code/{locale_code}", response_model=LocaleResponse)
@limiter.limit(get_rate_limit())
async def get_locale_by_code(
    request: Request,
    locale_code: str,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """
    Get a specific locale by code (e.g., 'en', 'fr', 'es').
    Supports both JWT and API key authentication.
    """
    locale = (
        db.query(Locale)
        .filter(
            Locale.code == locale_code,
            Locale.organization_id == current_user.organization_id,
        )
        .first()
    )

    if not locale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Locale with code '{locale_code}' not found",
        )

    return locale


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
    locale_ids: List[UUID],
    force_retranslate: bool,
    organization_id: UUID,
    db_ignored: Session,  # Keep parameter for backwards compat but don't use
    incremental: bool = False,
):
    """Background task to translate content entry.
    Only translates fields marked with localized: true in the content type schema.

    Args:
        incremental: If True, only translate fields missing from existing translation
    """
    import logging

    from backend.db.session import SessionLocal

    logger = logging.getLogger(__name__)

    # Create our own database session for the background task
    db = SessionLocal()

    try:
        translation_service = get_translation_service()
        logger.info(f"Starting translation for entry {entry_id} to locales {locale_ids}")

        # Get content entry with content type
        entry = (
            db.query(ContentEntry)
            .join(ContentType)
            .filter(ContentEntry.id == entry_id, ContentType.organization_id == organization_id)
            .first()
        )

        if not entry:
            logger.warning(f"Content entry {entry_id} not found")
            return

        # Get content type to check schema for localized fields
        content_type = entry.content_type

        # Parse entry data
        entry_data = json.loads(entry.data) if entry.data else {}
        logger.info(f"Entry data fields: {list(entry_data.keys())}")

        # Extract translatable fields from content type schema
        # Only fields with localized: true should be translated
        translatable_fields = None
        if content_type and content_type.fields_schema:
            # Handle fields_schema which may be JSON, Python-style string, or already a list/dict
            schema_fields = content_type.fields_schema
            if isinstance(schema_fields, str):
                try:
                    schema_fields = json.loads(schema_fields)
                except json.JSONDecodeError:
                    # Try parsing as Python literal (handles True/False/None and single quotes)
                    import ast

                    try:
                        schema_fields = ast.literal_eval(schema_fields)
                    except (ValueError, SyntaxError):
                        schema_fields = []
            translatable_fields = []

            # Schema can be either a list of field objects or a dict
            if isinstance(schema_fields, list):
                # List format: [{"name": "field_name", "type": "text", "localized": true}, ...]
                for field in schema_fields:
                    if isinstance(field, dict):
                        field_name = field.get("name")
                        if field_name and field.get("localized", True):
                            translatable_fields.append(field_name)
            elif isinstance(schema_fields, dict):
                # Dict format: {"field_name": {"type": "text", "localized": true}, ...}
                for field_name, field_config in schema_fields.items():
                    if isinstance(field_config, dict):
                        if field_config.get("localized", True):
                            translatable_fields.append(field_name)
                    else:
                        # If field config is not a dict, include it by default
                        translatable_fields.append(field_name)

            # If no fields are translatable, use None to translate all (backward compat)
            if not translatable_fields:
                translatable_fields = None

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
        logger.info(f"Found {len(locales)} locales to translate to")

        for locale in locales:
            logger.info(f"Processing locale: {locale.code}")
            # Check if translation exists
            existing_translation = (
                db.query(Translation)
                .filter(
                    Translation.content_entry_id == entry_id, Translation.locale_id == locale.id
                )
                .first()
            )

            if existing_translation and not force_retranslate and not incremental:
                logger.info(f"Translation already exists for {locale.code}, skipping")
                continue

            # For incremental mode, find missing fields
            data_to_translate = entry_data
            existing_data = {}

            if incremental and existing_translation:
                existing_data = (
                    json.loads(existing_translation.translated_data)
                    if isinstance(existing_translation.translated_data, str)
                    else existing_translation.translated_data
                )

                # Only translate fields that are missing from existing translation
                missing_fields = {k: v for k, v in entry_data.items() if k not in existing_data}

                if not missing_fields:
                    # No missing fields, skip this locale
                    continue

                data_to_translate = missing_fields
                # Update translatable_fields to only include missing ones
                if translatable_fields:
                    translatable_fields_for_locale = [
                        f for f in translatable_fields if f in missing_fields
                    ]
                else:
                    translatable_fields_for_locale = None
            else:
                translatable_fields_for_locale = translatable_fields

            # Translate the content, respecting localized field settings
            logger.info(f"Translating to {locale.code}, data: {list(data_to_translate.keys())}")
            translated_data = translation_service.translate_dict(
                data_to_translate,
                target_lang=locale.code.split("-")[0],  # Use base language code
                source_lang=None,
                translatable_fields=translatable_fields_for_locale,
            )
            logger.info(f"Translation result for {locale.code}: {list(translated_data.keys())}")

            if existing_translation:
                if incremental:
                    # Merge new translations with existing ones
                    merged_data = {**existing_data, **translated_data}
                    existing_translation.translated_data = json.dumps(merged_data)
                else:
                    # Replace entirely
                    existing_translation.translated_data = json.dumps(translated_data)
                existing_translation.status = "completed"
                existing_translation.translation_service = translation_service.provider
                existing_translation.version += 1
                logger.info(f"Updated existing translation for locale {locale.code}")
            else:
                # Create new translation using actual provider
                translation = Translation(
                    content_entry_id=entry_id,
                    locale_id=locale.id,
                    translated_data=json.dumps(translated_data),
                    status="completed",
                    translation_service=translation_service.provider,
                    quality_score=0.95,
                )
                db.add(translation)
                logger.info(f"Created new translation for locale {locale.code}")

        db.commit()
        logger.info(f"Translation completed for entry {entry_id}")

    except Exception as e:
        logger.error(f"Translation failed for entry {entry_id}: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


@router.post("/translate", response_model=TranslateResponse)
@limiter.limit(get_rate_limit())
async def translate_content(
    request: Request,
    translate_req: TranslateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user_flexible),
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
        translate_req.incremental,
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
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
    content_entry_id: Optional[UUID] = Query(None),
    locale_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    """
    List translations with pagination and filters.
    Supports both JWT and API key authentication.
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


@router.get("/translations/by-entry/{content_entry_id}")
@limiter.limit(get_rate_limit())
async def get_translations_by_entry(
    request: Request,
    content_entry_id: UUID,
    locale_code: Optional[str] = Query(
        None, description="Filter by locale code (e.g., 'es', 'fr')"
    ),
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """
    Get translations for a specific content entry.
    Optionally filter by locale code.
    Supports both JWT and API key authentication.

    Returns the translated_data directly for easy consumption.
    """
    query = (
        db.query(Translation)
        .join(ContentEntry)
        .join(ContentType)
        .filter(
            Translation.content_entry_id == content_entry_id,
            ContentType.organization_id == current_user.organization_id,
        )
    )

    # If locale_code provided, filter by it
    if locale_code:
        # Join with Locale to filter by code
        query = query.join(Locale, Translation.locale_id == Locale.id).filter(
            Locale.code == locale_code
        )

    translations = query.all()

    if not translations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No translations found for entry {content_entry_id}",
        )

    # Build response with locale codes
    result = []
    for trans in translations:
        locale = db.query(Locale).filter(Locale.id == trans.locale_id).first()
        translated_data = json.loads(trans.translated_data) if trans.translated_data else {}
        result.append(
            {
                "locale_code": locale.code if locale else None,
                "locale_name": locale.name if locale else None,
                "translated_data": translated_data,
                "status": trans.status,
                "translation_id": str(trans.id),
            }
        )

    # If single locale requested, return just that translation's data
    if locale_code and len(result) == 1:
        return result[0]

    return {"translations": result, "total": len(result)}


@router.get("/translations/{translation_id}", response_model=TranslationResponse)
@limiter.limit(get_rate_limit())
async def get_translation(
    request: Request,
    translation_id: UUID,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """
    Get a specific translation by ID.
    Supports both JWT and API key authentication.
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
