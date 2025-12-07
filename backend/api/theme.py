"""Theme management API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from backend.api.schemas.theme import (
    ThemeCreate,
    ThemeCSSVariables,
    ThemeListResponse,
    ThemeResponse,
    ThemeSetActive,
    ThemeUpdate,
)
from backend.core.default_themes import DEFAULT_THEMES, get_default_active_theme
from backend.core.dependencies import get_current_user, get_current_user_flexible
from backend.core.permissions import PermissionChecker
from backend.db.session import get_db
from backend.models.theme import Theme
from backend.models.user import User

router = APIRouter(prefix="/themes", tags=["themes"])


@router.post("", response_model=ThemeResponse, status_code=status.HTTP_201_CREATED)
def create_theme(
    theme_data: ThemeCreate,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """
    Create a new custom theme for the organization.

    Requires 'themes.manage' permission.
    """
    # Check permission
    if not PermissionChecker.has_permission(current_user, "themes.manage", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage themes",
        )

    # Check if theme name already exists in this organization
    existing = (
        db.query(Theme)
        .filter(
            and_(
                Theme.organization_id == current_user.organization_id,
                Theme.name == theme_data.name,
            )
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Theme with name '{theme_data.name}' already exists",
        )

    # Create theme
    theme = Theme(
        organization_id=current_user.organization_id,
        name=theme_data.name,
        display_name=theme_data.display_name,
        description=theme_data.description,
        is_system_theme=False,  # Custom themes are never system themes
        is_active=False,  # New themes are inactive by default
        colors=theme_data.colors.model_dump(),
        typography=theme_data.typography.model_dump() if theme_data.typography else None,
        spacing=theme_data.spacing,
        borderRadius=theme_data.borderRadius,
        shadows=theme_data.shadows,
        custom_properties=theme_data.custom_properties,
    )

    db.add(theme)
    db.commit()
    db.refresh(theme)

    return theme


@router.get("", response_model=ThemeListResponse)
def list_themes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    include_system: bool = Query(True, description="Include system themes"),
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """
    List all themes for the organization.

    Includes both custom themes and system themes (if include_system=True).
    """
    query = db.query(Theme).filter(Theme.organization_id == current_user.organization_id)

    if not include_system:
        query = query.filter(Theme.is_system_theme == False)

    # Count total
    total = query.count()

    # Paginate
    offset = (page - 1) * page_size
    themes = (
        query.order_by(Theme.is_active.desc(), Theme.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return ThemeListResponse(
        themes=themes,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{theme_id}", response_model=ThemeResponse)
def get_theme(
    theme_id: UUID,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """Get a specific theme by ID."""
    theme = (
        db.query(Theme)
        .filter(
            and_(
                Theme.id == theme_id,
                Theme.organization_id == current_user.organization_id,
            )
        )
        .first()
    )

    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found",
        )

    return theme


@router.get("/active/current", response_model=ThemeResponse)
def get_active_theme(
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """
    Get the currently active theme for the organization.

    If no theme is set as active, returns the default Dark Chocolate theme.
    Supports both JWT and API key authentication.
    """
    active_theme = (
        db.query(Theme)
        .filter(
            and_(
                Theme.organization_id == current_user.organization_id,
                Theme.is_active == True,
            )
        )
        .first()
    )

    if not active_theme:
        # Return default theme (but don't create it in DB yet)
        default = get_default_active_theme()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active theme set. Use POST /themes/initialize-defaults to create default themes.",
        )

    return active_theme


@router.patch("/{theme_id}", response_model=ThemeResponse)
def update_theme(
    theme_id: UUID,
    theme_data: ThemeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a theme.

    Requires 'themes.manage' permission.
    System themes cannot be updated.
    """
    # Check permission
    # Fixed: Use static method
    if not PermissionChecker.has_permission(current_user, "themes.manage", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage themes",
        )

    # Get theme
    theme = (
        db.query(Theme)
        .filter(
            and_(
                Theme.id == theme_id,
                Theme.organization_id == current_user.organization_id,
            )
        )
        .first()
    )

    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found",
        )

    # Prevent updating system themes
    if theme.is_system_theme:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update system themes. Clone it to create a custom version.",
        )

    # Update fields
    update_data = theme_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "colors" and value:
            setattr(theme, field, value.model_dump())
        elif field == "typography" and value:
            setattr(theme, field, value.model_dump())
        else:
            setattr(theme, field, value)

    db.commit()
    db.refresh(theme)

    return theme


@router.delete("/{theme_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_theme(
    theme_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a theme.

    Requires 'themes.manage' permission.
    System themes and active themes cannot be deleted.
    """
    # Check permission
    # Fixed: Use static method
    if not PermissionChecker.has_permission(current_user, "themes.manage", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage themes",
        )

    # Get theme
    theme = (
        db.query(Theme)
        .filter(
            and_(
                Theme.id == theme_id,
                Theme.organization_id == current_user.organization_id,
            )
        )
        .first()
    )

    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found",
        )

    # Prevent deleting system themes
    if theme.is_system_theme:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system themes",
        )

    # Prevent deleting active theme
    if theme.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the active theme. Set another theme as active first.",
        )

    db.delete(theme)
    db.commit()


@router.post("/set-active", response_model=ThemeResponse)
def set_active_theme(
    data: ThemeSetActive,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Set a theme as the active theme for the organization.

    Requires 'themes.manage' permission.
    Only one theme can be active at a time.
    """
    # Check permission
    # Fixed: Use static method
    if not PermissionChecker.has_permission(current_user, "themes.manage", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage themes",
        )

    # Get the theme to activate
    theme = (
        db.query(Theme)
        .filter(
            and_(
                Theme.id == data.theme_id,
                Theme.organization_id == current_user.organization_id,
            )
        )
        .first()
    )

    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found",
        )

    # Deactivate all other themes
    db.query(Theme).filter(Theme.organization_id == current_user.organization_id).update(
        {"is_active": False}
    )

    # Activate this theme
    theme.is_active = True
    db.commit()
    db.refresh(theme)

    return theme


@router.post("/{theme_id}/activate", response_model=ThemeResponse)
def activate_theme(
    theme_id: UUID,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """
    Activate a theme for the organization (alternative endpoint for UI).

    Requires 'themes.manage' permission.
    Only one theme can be active at a time.
    """
    # Check permission
    if not PermissionChecker.has_permission(current_user, "themes.manage", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage themes",
        )

    # Get the theme to activate
    theme = (
        db.query(Theme)
        .filter(
            and_(
                Theme.id == theme_id,
                Theme.organization_id == current_user.organization_id,
            )
        )
        .first()
    )

    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found",
        )

    # Deactivate all other themes
    db.query(Theme).filter(Theme.organization_id == current_user.organization_id).update(
        {"is_active": False}
    )

    # Activate this theme
    theme.is_active = True
    db.commit()
    db.refresh(theme)

    return theme


@router.post("/{theme_id}/deactivate", response_model=ThemeResponse)
def deactivate_theme(
    theme_id: UUID,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """
    Deactivate a theme for the organization.

    Requires 'themes.manage' permission.
    """
    # Check permission
    if not PermissionChecker.has_permission(current_user, "themes.manage", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage themes",
        )

    # Get the theme to deactivate
    theme = (
        db.query(Theme)
        .filter(
            and_(
                Theme.id == theme_id,
                Theme.organization_id == current_user.organization_id,
            )
        )
        .first()
    )

    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found",
        )

    # Deactivate this theme
    theme.is_active = False
    db.commit()
    db.refresh(theme)

    return theme


@router.get("/{theme_id}/export")
def export_theme(
    theme_id: UUID,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """
    Export theme configuration as JSON.

    Returns the complete theme definition that can be imported elsewhere.
    """
    theme = (
        db.query(Theme)
        .filter(
            and_(
                Theme.id == theme_id,
                Theme.organization_id == current_user.organization_id,
            )
        )
        .first()
    )

    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found",
        )

    # Export as dictionary
    export_data = {
        "name": theme.name,
        "display_name": theme.display_name,
        "description": theme.description,
        "colors": theme.colors,
        "typography": theme.typography,
        "spacing": theme.spacing,
        "borderRadius": theme.borderRadius,
        "shadows": theme.shadows,
        "custom_properties": theme.custom_properties,
    }

    return export_data


@router.get("/{theme_id}/css-variables", response_model=ThemeCSSVariables)
def get_theme_css_variables(
    theme_id: UUID,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """
    Get CSS custom properties (variables) for a theme.

    Returns both a dictionary and a CSS string ready to use in :root.
    """
    theme = (
        db.query(Theme)
        .filter(
            and_(
                Theme.id == theme_id,
                Theme.organization_id == current_user.organization_id,
            )
        )
        .first()
    )

    if not theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Theme not found",
        )

    # Get CSS variables
    css_vars = theme.to_css_variables()

    # Generate CSS string
    css_lines = [":root {"]
    for var_name, var_value in css_vars.items():
        css_lines.append(f"  {var_name}: {var_value};")
    css_lines.append("}")
    css_string = "\n".join(css_lines)

    return ThemeCSSVariables(
        theme_id=theme.id,
        theme_name=theme.name,
        css_variables=css_vars,
        css_string=css_string,
    )


@router.post("/initialize-defaults", response_model=dict)
def initialize_default_themes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Initialize default system themes for the organization.

    Creates Dark Chocolate, Light, and Dark themes if they don't exist.
    Sets Dark Chocolate as the active theme.

    Requires 'themes.manage' permission.
    """
    # Check permission
    # Fixed: Use static method
    if not PermissionChecker.has_permission(current_user, "themes.manage", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage themes",
        )

    created_themes = []

    for default_theme in DEFAULT_THEMES:
        # Check if theme already exists
        existing = (
            db.query(Theme)
            .filter(
                and_(
                    Theme.organization_id == current_user.organization_id,
                    Theme.name == default_theme["name"],
                )
            )
            .first()
        )

        if not existing:
            # Create theme
            theme = Theme(
                organization_id=current_user.organization_id,
                name=default_theme["name"],
                display_name=default_theme["display_name"],
                description=default_theme["description"],
                is_system_theme=True,
                is_active=(
                    default_theme["name"] == "dark-chocolate"
                ),  # Set Dark Chocolate as active
                colors=default_theme["colors"],
                typography=default_theme.get("typography"),
                spacing=default_theme.get("spacing"),
                borderRadius=default_theme.get("borderRadius"),
                shadows=default_theme.get("shadows"),
            )
            db.add(theme)
            created_themes.append(default_theme["name"])

    db.commit()

    return {
        "message": (
            "Default themes initialized" if created_themes else "Default themes already exist"
        ),
        "created": created_themes,
        "total_themes": len(DEFAULT_THEMES),
    }


@router.post("/{theme_id}/clone", response_model=ThemeResponse, status_code=status.HTTP_201_CREATED)
def clone_theme(
    theme_id: UUID,
    new_name: str = Query(..., description="Name for the cloned theme"),
    new_display_name: str = Query(..., description="Display name for the cloned theme"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Clone an existing theme (system or custom) to create a new custom theme.

    Useful for customizing system themes.
    Requires 'themes.manage' permission.
    """
    # Check permission
    # Fixed: Use static method
    if not PermissionChecker.has_permission(current_user, "themes.manage", db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to manage themes",
        )

    # Get source theme
    source_theme = (
        db.query(Theme)
        .filter(
            and_(
                Theme.id == theme_id,
                Theme.organization_id == current_user.organization_id,
            )
        )
        .first()
    )

    if not source_theme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source theme not found",
        )

    # Check if new name already exists
    existing = (
        db.query(Theme)
        .filter(
            and_(
                Theme.organization_id == current_user.organization_id,
                Theme.name == new_name,
            )
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Theme with name '{new_name}' already exists",
        )

    # Clone theme
    cloned_theme = Theme(
        organization_id=current_user.organization_id,
        name=new_name,
        display_name=new_display_name,
        description=f"Cloned from {source_theme.display_name}",
        is_system_theme=False,  # Clones are always custom themes
        is_active=False,
        colors=source_theme.colors,
        typography=source_theme.typography,
        spacing=source_theme.spacing,
        borderRadius=source_theme.borderRadius,
        shadows=source_theme.shadows,
        custom_properties=source_theme.custom_properties,
    )

    db.add(cloned_theme)
    db.commit()
    db.refresh(cloned_theme)

    return cloned_theme
