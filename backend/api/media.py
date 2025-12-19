"""
Media Management API Endpoints
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.api.schemas.media import (
    BulkDeleteRequest,
    BulkDeleteResponse,
    MediaListResponse,
    MediaResponse,
    MediaStats,
    MediaType,
    MediaUpdateRequest,
    MediaUploadResponse,
    ThumbnailRequest,
    ThumbnailResponse,
)
from backend.core.cache_middleware import add_cache_headers
from backend.core.dependencies import get_current_user_flexible
from backend.core.media_utils import (
    create_thumbnail,
    ensure_upload_directories,
    generate_unique_filename,
    get_file_extension,
    get_image_dimensions,
    get_media_type,
    get_mime_type,
    validate_file_extension,
    validate_file_size,
)
from backend.core.rate_limit import get_rate_limit, limiter
from backend.core.storage import get_storage_backend
from backend.core.webhook_service import publish_media_deleted_sync, publish_media_uploaded_sync
from backend.db.session import get_db
from backend.models.media import Media
from backend.models.user import User

router = APIRouter(prefix="/media", tags=["media"])

# Ensure upload directories exist on module load
ensure_upload_directories()


@router.post("/upload", response_model=MediaUploadResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(get_rate_limit())
async def upload_media(
    request: Request,
    file: UploadFile = File(...),
    alt_text: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[str] = None,  # JSON array as string
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """
    Upload a media file

    Args:
        file: File to upload
        alt_text: Alt text for accessibility
        description: File description
        tags: Tags as JSON array string

    Returns:
        MediaUploadResponse with file details
    """
    # Validate filename extension
    is_valid, error_msg = validate_file_extension(file.filename)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    # Read file content
    file_content = await file.read()
    file_size = len(file_content)

    # Get MIME type
    mime_type = file.content_type or get_mime_type(file.filename)
    extension = get_file_extension(file.filename)

    # Validate file size
    is_valid, error_msg = validate_file_size(file_size, mime_type, extension)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    # Generate unique filename
    unique_filename = generate_unique_filename(file.filename)
    media_type_cat = get_media_type(mime_type, extension)

    # Get storage backend
    storage = get_storage_backend()

    # Prepare storage path (relative path for storage backend)
    relative_path = f"{current_user.organization_id}/{media_type_cat}/{unique_filename}"

    # Save file using storage backend
    try:
        file_url = storage.save_file(file_content, relative_path)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}",
        )

    # Get image dimensions if image
    width, height = None, None
    if media_type_cat == "image":
        # For local storage, get dimensions from file
        # For S3, we'll need to download temporarily or skip
        from backend.core.storage import LocalStorageBackend

        if isinstance(storage, LocalStorageBackend):
            storage_path = storage.get_full_path(relative_path)
            dimensions = get_image_dimensions(storage_path)
            if dimensions:
                width, height = dimensions

    # Create media record
    media = Media(
        organization_id=current_user.organization_id,
        uploaded_by_id=current_user.id,
        filename=unique_filename,
        original_filename=file.filename,
        file_path=relative_path,
        url=file_url,
        mime_type=mime_type,
        file_size=file_size,
        file_extension=extension,
        media_type=media_type_cat,
        width=width,
        height=height,
        alt_text=alt_text,
        description=description,
        tags=tags,
    )

    db.add(media)
    db.commit()
    db.refresh(media)

    # Publish webhook event
    if background_tasks:
        background_tasks.add_task(
            publish_media_uploaded_sync,
            media.id,
            current_user.organization_id,
            db,
        )

    return MediaUploadResponse(
        id=media.id,
        filename=media.filename,
        original_filename=media.original_filename,
        url=media.url,
        mime_type=media.mime_type,
        file_size=media.file_size,
        media_type=MediaType(media.media_type),
        width=media.width,
        height=media.height,
        created_at=media.created_at,
    )


@router.get("", response_model=MediaListResponse)
@limiter.limit(get_rate_limit())
async def list_media(
    request: Request,
    media_type: Optional[MediaType] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """
    List media files with filtering and pagination

    Args:
        media_type: Filter by media type
        search: Search in filename and description
        page: Page number
        page_size: Items per page

    Returns:
        Paginated list of media files
    """
    # Build query
    query = select(Media).where(Media.organization_id == current_user.organization_id)

    # Apply filters
    if media_type:
        query = query.where(Media.media_type == media_type.value)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Media.original_filename.ilike(search_pattern),
                Media.description.ilike(search_pattern),
                Media.alt_text.ilike(search_pattern),
            )
        )

    # Get total count
    total_query = select(func.count()).select_from(query.subquery())
    total = db.execute(total_query).scalar_one()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(Media.created_at.desc()).offset(offset).limit(page_size)

    # Execute query
    media_items = db.execute(query).scalars().all()

    # Parse tags for each item
    items = []
    for item in media_items:
        item_dict = MediaResponse.model_validate(item).model_dump()
        if item.tags:
            try:
                item_dict["tags"] = json.loads(item.tags)
            except:
                item_dict["tags"] = []
        items.append(MediaResponse(**item_dict))

    total_pages = (total + page_size - 1) // page_size

    return MediaListResponse(
        items=items, total=total, page=page, page_size=page_size, total_pages=total_pages
    )


@router.get("/search", response_model=MediaListResponse)
@limiter.limit(get_rate_limit())
async def search_media(
    request: Request,
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    media_type: Optional[MediaType] = None,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """
    Search media files by filename, alt_text, or description.
    Supports filtering by media type.
    """
    # Base query
    query = select(Media).where(Media.organization_id == current_user.organization_id)

    # Search across filename, alt_text, and description
    search_filter = or_(
        Media.filename.ilike(f"%{q}%"),
        Media.alt_text.ilike(f"%{q}%"),
        Media.description.ilike(f"%{q}%"),
    )
    query = query.where(search_filter)

    # Filter by media type if specified
    if media_type:
        query = query.where(Media.content_type.startswith(media_type.value))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Media.created_at.desc())

    # Execute
    media_items = db.execute(query).scalars().all()

    # Parse tags
    items = []
    for item in media_items:
        item_dict = MediaResponse.model_validate(item).model_dump()
        if item.tags:
            try:
                item_dict["tags"] = json.loads(item.tags)
            except:
                item_dict["tags"] = []
        items.append(MediaResponse(**item_dict))

    total_pages = (total + page_size - 1) // page_size

    return MediaListResponse(
        items=items, total=total, page=page, page_size=page_size, total_pages=total_pages
    )


@router.get("/{media_id}", response_model=MediaResponse)
@limiter.limit(get_rate_limit())
async def get_media(
    request: Request,
    media_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """Get media file details"""
    media = db.execute(
        select(Media).where(
            Media.id == media_id, Media.organization_id == current_user.organization_id
        )
    ).scalar_one_or_none()

    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")

    # Parse tags
    response_dict = MediaResponse.model_validate(media).model_dump()
    if media.tags:
        try:
            response_dict["tags"] = json.loads(media.tags)
        except:
            response_dict["tags"] = []

    return MediaResponse(**response_dict)


@router.put("/{media_id}", response_model=MediaResponse)
@limiter.limit(get_rate_limit())
async def update_media(
    request: Request,
    media_id: UUID,
    update_data: MediaUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """Update media metadata"""
    media = db.execute(
        select(Media).where(
            Media.id == media_id, Media.organization_id == current_user.organization_id
        )
    ).scalar_one_or_none()

    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")

    # Update fields
    if update_data.alt_text is not None:
        media.alt_text = update_data.alt_text

    if update_data.description is not None:
        media.description = update_data.description

    if update_data.tags is not None:
        media.tags = json.dumps(update_data.tags)

    media.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(media)

    # Parse tags for response
    response_dict = MediaResponse.model_validate(media).model_dump()
    if media.tags:
        try:
            response_dict["tags"] = json.loads(media.tags)
        except:
            response_dict["tags"] = []

    return MediaResponse(**response_dict)


@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(get_rate_limit())
async def delete_media(
    request: Request,
    media_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """Delete media file"""
    media = db.execute(
        select(Media).where(
            Media.id == media_id, Media.organization_id == current_user.organization_id
        )
    ).scalar_one_or_none()

    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")

    # Store ID and org for webhook before deletion
    media_id_val = media.id
    org_id = current_user.organization_id

    # Delete physical file using storage backend
    storage = get_storage_backend()
    storage.delete_file(media.file_path)

    # Delete from database
    db.delete(media)
    db.commit()

    # Publish webhook event
    background_tasks.add_task(
        publish_media_deleted_sync,
        media_id_val,
        org_id,
        db,
    )

    return None


@router.get("/files/{filename}")
@limiter.limit(get_rate_limit())
async def serve_media_file(request: Request, filename: str, db: Session = Depends(get_db)):
    """
    Serve media file

    Note: For S3 storage, this returns a redirect to the S3 URL.
    For local storage, it serves the file directly.
    """
    # Find media by filename
    media = db.execute(select(Media).where(Media.filename == filename)).scalar_one_or_none()

    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    storage = get_storage_backend()

    # Check if file exists
    if not storage.file_exists(media.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found in storage"
        )

    # For local storage, serve file directly
    from backend.core.storage import LocalStorageBackend

    if isinstance(storage, LocalStorageBackend):
        file_path = storage.get_full_path(media.file_path)
        response = FileResponse(
            path=file_path, media_type=media.mime_type, filename=media.original_filename
        )
        # Add CDN cache headers (1 year for immutable media)
        add_cache_headers(response, max_age=31536000, public=True)
        return response

    # For S3, redirect to S3 URL
    from fastapi.responses import RedirectResponse

    file_url = storage.get_file_url(media.file_path)
    response = RedirectResponse(url=file_url)
    # Add cache headers for redirect
    add_cache_headers(response, max_age=3600, public=True)
    return response


@router.get("/proxy/{filename}")
@limiter.limit(get_rate_limit())
async def proxy_media_file(request: Request, filename: str, db: Session = Depends(get_db)):
    """
    Proxy media file - streams the file content directly instead of redirecting.

    This endpoint is useful when the storage backend (e.g., MinIO) is not
    publicly accessible and you need to serve files through the API.

    Note: For large files, consider using the redirect endpoint instead.
    """
    from fastapi.responses import Response

    # Find media by filename
    media = db.execute(select(Media).where(Media.filename == filename)).scalar_one_or_none()

    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    storage = get_storage_backend()

    # Check if file exists
    if not storage.file_exists(media.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found in storage"
        )

    # For local storage, serve file directly
    from backend.core.storage import LocalStorageBackend

    if isinstance(storage, LocalStorageBackend):
        file_path = storage.get_full_path(media.file_path)
        response = FileResponse(
            path=file_path, media_type=media.mime_type, filename=media.original_filename
        )
        add_cache_headers(response, max_age=31536000, public=True)
        return response

    # For S3, download and stream the content
    from backend.core.storage import S3StorageBackend

    if isinstance(storage, S3StorageBackend):
        try:
            content, content_type = storage.get_file_content(media.file_path)
            response = Response(
                content=content,
                media_type=media.mime_type or content_type,
                headers={
                    "Content-Disposition": f'inline; filename="{media.original_filename}"',
                },
            )
            add_cache_headers(response, max_age=31536000, public=True)
            return response
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve file: {str(e)}",
            )

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unknown storage backend"
    )


@router.post("/thumbnail", response_model=ThumbnailResponse)
@limiter.limit(get_rate_limit())
async def generate_thumbnail(
    request: Request,
    thumbnail_request: ThumbnailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """Generate thumbnail for image"""
    media = db.execute(
        select(Media).where(
            Media.id == thumbnail_request.media_id,
            Media.organization_id == current_user.organization_id,
        )
    ).scalar_one_or_none()

    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")

    if media.media_type != "image":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thumbnail generation only supported for images",
        )

    storage = get_storage_backend()

    # For S3 storage, we need to download the file first
    import tempfile

    from backend.core.storage import S3StorageBackend

    if isinstance(storage, S3StorageBackend):
        # Download from S3 to temp file
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=Path(media.filename).suffix
        ) as tmp_file:
            tmp_path = Path(tmp_file.name)
            # Download file content

            s3_client = storage.s3_client
            s3_client.download_file(storage.bucket_name, media.file_path, str(tmp_path))
            source_path = tmp_path
    else:
        source_path = storage.get_full_path(media.file_path)
        if not source_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Source file not found"
            )

    # Generate thumbnail filename
    thumb_filename = (
        f"thumb_{thumbnail_request.width or 300}x{thumbnail_request.height or 300}_{media.filename}"
    )

    # Create thumbnail in temp location first
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_thumb_path = Path(tmpdir) / thumb_filename

        # Create thumbnail
        width, height = create_thumbnail(
            source_path,
            temp_thumb_path,
            max_width=thumbnail_request.width or 300,
            max_height=thumbnail_request.height or 300,
            quality=thumbnail_request.quality,
        )

        # Read thumbnail content
        with open(temp_thumb_path, "rb") as f:
            thumb_content = f.read()

        # Upload thumbnail to storage
        thumb_relative_path = f"thumbnails/{thumb_filename}"
        thumb_url = storage.save_file(thumb_content, thumb_relative_path)

    # Clean up temp file if S3
    if isinstance(storage, S3StorageBackend):
        source_path.unlink()

    # Update media record with thumbnail info
    media.thumbnail_path = thumb_relative_path
    media.thumbnail_url = thumb_url
    db.commit()

    return ThumbnailResponse(media_id=media.id, thumbnail_url=thumb_url, width=width, height=height)


@router.get("/thumbnails/{filename}")
@limiter.limit(get_rate_limit())
async def serve_thumbnail(request: Request, filename: str, db: Session = Depends(get_db)):
    """
    Serve thumbnail file

    Note: For S3 storage, this returns a redirect to the S3 URL.
    For local storage, it serves the file directly.
    """
    # Find media by thumbnail filename
    thumb_path_pattern = f"thumbnails/{filename}"
    media = db.execute(
        select(Media).where(Media.thumbnail_path == thumb_path_pattern)
    ).scalar_one_or_none()

    if not media or not media.thumbnail_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail not found")

    storage = get_storage_backend()

    # For local storage, serve file directly
    from backend.core.storage import LocalStorageBackend

    if isinstance(storage, LocalStorageBackend):
        thumb_path = storage.get_full_path(media.thumbnail_path)
        if not thumb_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail file not found"
            )
        return FileResponse(path=thumb_path, media_type="image/jpeg")

    # For S3, redirect to S3 URL
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url=media.thumbnail_url)


@router.get("/stats/overview", response_model=MediaStats)
@limiter.limit(get_rate_limit())
async def get_media_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """Get media storage statistics"""
    # Total files
    total_files = db.execute(
        select(func.count()).where(Media.organization_id == current_user.organization_id)
    ).scalar_one()

    # Total size
    total_size = (
        db.execute(
            select(func.sum(Media.file_size)).where(
                Media.organization_id == current_user.organization_id
            )
        ).scalar_one()
        or 0
    )

    # Count by type
    by_type_query = (
        select(Media.media_type, func.count(Media.id).label("count"))
        .where(Media.organization_id == current_user.organization_id)
        .group_by(Media.media_type)
    )

    by_type = {row[0]: row[1] for row in db.execute(by_type_query).all()}

    # Count by MIME type
    by_mime_query = (
        select(Media.mime_type, func.count(Media.id).label("count"))
        .where(Media.organization_id == current_user.organization_id)
        .group_by(Media.mime_type)
    )

    by_mime_type = {row[0]: row[1] for row in db.execute(by_mime_query).all()}

    return MediaStats(
        total_files=total_files, total_size=total_size, by_type=by_type, by_mime_type=by_mime_type
    )


@router.post("/bulk-delete", response_model=BulkDeleteResponse)
@limiter.limit(get_rate_limit())
async def bulk_delete_media(
    request: Request,
    delete_request: BulkDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_flexible),
):
    """Delete multiple media files"""
    deleted_count = 0
    failed_ids = []
    errors = []

    storage = get_storage_backend()

    for media_id in delete_request.media_ids:
        try:
            media = db.execute(
                select(Media).where(
                    Media.id == media_id, Media.organization_id == current_user.organization_id
                )
            ).scalar_one_or_none()

            if not media:
                failed_ids.append(media_id)
                errors.append(f"Media {media_id} not found")
                continue

            # Delete physical file using storage backend
            storage.delete_file(media.file_path)

            # Delete thumbnail if exists
            if media.thumbnail_path:
                storage.delete_file(media.thumbnail_path)

            # Delete from database
            db.delete(media)
            deleted_count += 1

        except Exception as e:
            failed_ids.append(media_id)
            errors.append(f"Media {media_id}: {str(e)}")

    db.commit()

    return BulkDeleteResponse(deleted_count=deleted_count, failed_ids=failed_ids, errors=errors)
