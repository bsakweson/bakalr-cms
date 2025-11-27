"""
Content relationship management endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from backend.api.schemas.relationship import (
    ContentRelationshipCreate,
    ContentRelationshipResponse,
    ContentRelationshipUpdate,
    RelatedContentResponse,
)
from backend.core.dependencies import get_current_user, get_db
from backend.core.rate_limit import get_rate_limit, limiter
from backend.models.content import ContentEntry
from backend.models.relationship import ContentRelationship
from backend.models.user import User

router = APIRouter(prefix="/content/relationships", tags=["relationships"])


@router.post(
    "/entries/{entry_id}/relationships",
    response_model=ContentRelationshipResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(get_rate_limit())
async def create_relationship(
    request: Request,
    entry_id: int,
    data: ContentRelationshipCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a relationship between two content entries.

    Examples:
    - Link blog post to author: POST /entries/123/relationships {"target_entry_id": 456, "relationship_type": "author"}
    - Add tag to post: POST /entries/123/relationships {"target_entry_id": 789, "relationship_type": "tags"}
    """
    # Verify source entry exists
    source = db.query(ContentEntry).filter(ContentEntry.id == entry_id).first()
    if not source:
        raise HTTPException(status_code=404, detail=f"Source entry {entry_id} not found")

    # Verify target entry exists
    target = db.query(ContentEntry).filter(ContentEntry.id == data.target_entry_id).first()
    if not target:
        raise HTTPException(
            status_code=404, detail=f"Target entry {data.target_entry_id} not found"
        )

    # Check for existing relationship
    existing = (
        db.query(ContentRelationship)
        .filter(
            and_(
                ContentRelationship.source_entry_id == entry_id,
                ContentRelationship.target_entry_id == data.target_entry_id,
                ContentRelationship.relationship_type == data.relationship_type,
            )
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Relationship already exists between entries {entry_id} and {data.target_entry_id}",
        )

    # Create relationship
    relationship = ContentRelationship(
        source_entry_id=entry_id,
        target_entry_id=data.target_entry_id,
        relationship_type=data.relationship_type,
        meta_data=data.meta_data,
    )

    db.add(relationship)
    db.commit()
    db.refresh(relationship)

    return relationship


@router.get("/entries/{entry_id}/relationships", response_model=List[ContentRelationshipResponse])
@limiter.limit(get_rate_limit())
async def list_relationships(
    request: Request,
    entry_id: int,
    relationship_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all relationships for a content entry.

    Optionally filter by relationship_type.
    """
    # Verify entry exists
    entry = db.query(ContentEntry).filter(ContentEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail=f"Entry {entry_id} not found")

    query = db.query(ContentRelationship).filter(ContentRelationship.source_entry_id == entry_id)

    if relationship_type:
        query = query.filter(ContentRelationship.relationship_type == relationship_type)

    return query.all()


@router.get("/entries/{entry_id}/related", response_model=List[RelatedContentResponse])
@limiter.limit(get_rate_limit())
async def get_related_content(
    request: Request,
    entry_id: int,
    relationship_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get related content with expansion (includes entry details).

    Returns the actual content entries linked through relationships.
    """
    # Verify entry exists
    entry = db.query(ContentEntry).filter(ContentEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail=f"Entry {entry_id} not found")

    query = (
        db.query(ContentRelationship, ContentEntry)
        .join(ContentEntry, ContentEntry.id == ContentRelationship.target_entry_id)
        .filter(ContentRelationship.source_entry_id == entry_id)
    )

    if relationship_type:
        query = query.filter(ContentRelationship.relationship_type == relationship_type)

    results = []
    for rel, target_entry in query.all():
        results.append(
            RelatedContentResponse(
                relationship_id=rel.id,
                relationship_type=rel.relationship_type,
                entry_id=target_entry.id,
                entry_title=target_entry.title,
                entry_slug=target_entry.slug,
                content_type_id=target_entry.content_type_id,
                meta_data=rel.meta_data,
            )
        )

    return results


@router.delete("/relationships/{relationship_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(get_rate_limit())
async def delete_relationship(
    request: Request,
    relationship_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a content relationship.
    """
    relationship = (
        db.query(ContentRelationship).filter(ContentRelationship.id == relationship_id).first()
    )

    if not relationship:
        raise HTTPException(status_code=404, detail=f"Relationship {relationship_id} not found")

    db.delete(relationship)
    db.commit()

    return None


@router.patch("/relationships/{relationship_id}", response_model=ContentRelationshipResponse)
@limiter.limit(get_rate_limit())
async def update_relationship(
    request: Request,
    relationship_id: int,
    data: ContentRelationshipUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a content relationship's metadata or type.
    """
    relationship = (
        db.query(ContentRelationship).filter(ContentRelationship.id == relationship_id).first()
    )

    if not relationship:
        raise HTTPException(status_code=404, detail=f"Relationship {relationship_id} not found")

    if data.relationship_type is not None:
        relationship.relationship_type = data.relationship_type

    if data.meta_data is not None:
        relationship.meta_data = data.meta_data

    db.commit()
    db.refresh(relationship)

    return relationship
