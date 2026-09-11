"""Routes for user profile, notification preferences, and security settings."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.auth.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.profile import ProfileUpdate, ProfileResponse
from app.schemas.notification_preferences import (
    NotificationPreferencesUpdate,
    NotificationPreferencesResponse,
)
from app.schemas.security_settings import SecuritySettingsResponse, SecuritySettingsUpdate
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/api/users/me", tags=["profile"])


# ------------------------------------------------------------------ profile

@router.get("/profile", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get the current user's profile."""
    profile = ProfileService.get_profile(db, current_user.id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return profile


@router.patch("/profile", response_model=ProfileResponse)
async def update_profile(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update the current user's profile."""
    return ProfileService.update_profile(db, current_user.id, data, actor_id=current_user.id)


# ------------------------------------------------ notification preferences

@router.get("/notifications", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get the current user's notification preferences."""
    prefs = ProfileService.get_notification_preferences(db, current_user.id)
    if not prefs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preferences not found")
    return prefs


@router.patch("/notifications", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    data: NotificationPreferencesUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update the current user's notification preferences."""
    return ProfileService.update_notification_preferences(
        db, current_user.id, data, actor_id=current_user.id
    )


# --------------------------------------------------- security settings

@router.get("/security", response_model=SecuritySettingsResponse)
async def get_security_settings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get the current user's security settings."""
    settings = ProfileService.get_security_settings(db, current_user.id)
    if not settings:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Security settings not found")
    return settings


@router.patch("/security", response_model=SecuritySettingsResponse)
async def update_security_settings(
    data: SecuritySettingsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update user-controllable security settings (e.g. session timeout)."""
    return ProfileService.update_security_settings(
        db, current_user.id, data, actor_id=current_user.id
    )
