"""Service for profile, notification preferences, and security settings."""

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.models.profile import UserProfile
from app.models.notification_preferences import NotificationPreferences
from app.models.security_settings import SecuritySettings
from app.schemas.profile import ProfileUpdate
from app.schemas.notification_preferences import NotificationPreferencesUpdate
from app.schemas.security_settings import SecuritySettingsUpdate


class ProfileService:

    # ------------------------------------------------------------------ profile

    @staticmethod
    def get_profile(db: Session, user_id: int) -> Optional[UserProfile]:
        return db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

    @staticmethod
    def update_profile(
        db: Session, user_id: int, data: ProfileUpdate, actor_id: int
    ) -> UserProfile:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            profile = UserProfile(user_id=user_id)
            db.add(profile)

        update_data = data.model_dump(exclude_none=True)
        for field, value in update_data.items():
            setattr(profile, field, value)
        profile.updated_by = actor_id

        db.commit()
        db.refresh(profile)
        return profile

    # ------------------------------------------------ notification preferences

    @staticmethod
    def get_notification_preferences(
        db: Session, user_id: int
    ) -> Optional[NotificationPreferences]:
        return (
            db.query(NotificationPreferences)
            .filter(NotificationPreferences.user_id == user_id)
            .first()
        )

    @staticmethod
    def update_notification_preferences(
        db: Session, user_id: int, data: NotificationPreferencesUpdate, actor_id: int
    ) -> NotificationPreferences:
        prefs = (
            db.query(NotificationPreferences)
            .filter(NotificationPreferences.user_id == user_id)
            .first()
        )
        if not prefs:
            prefs = NotificationPreferences(user_id=user_id)
            db.add(prefs)

        update_data = data.model_dump(exclude_none=True)
        for field, value in update_data.items():
            setattr(prefs, field, value)
        prefs.updated_by = actor_id

        db.commit()
        db.refresh(prefs)
        return prefs

    # --------------------------------------------------- security settings

    @staticmethod
    def get_security_settings(db: Session, user_id: int) -> Optional[SecuritySettings]:
        return (
            db.query(SecuritySettings)
            .filter(SecuritySettings.user_id == user_id)
            .first()
        )

    @staticmethod
    def update_security_settings(
        db: Session, user_id: int, data: SecuritySettingsUpdate, actor_id: int
    ) -> SecuritySettings:
        settings = (
            db.query(SecuritySettings)
            .filter(SecuritySettings.user_id == user_id)
            .first()
        )
        if not settings:
            settings = SecuritySettings(user_id=user_id)
            db.add(settings)

        update_data = data.model_dump(exclude_none=True)
        for field, value in update_data.items():
            setattr(settings, field, value)
        settings.updated_by = actor_id

        db.commit()
        db.refresh(settings)
        return settings

    @staticmethod
    def record_login(db: Session, user_id: int, ip_address: Optional[str]) -> None:
        """Called after a successful login to update tracking fields."""
        settings = (
            db.query(SecuritySettings)
            .filter(SecuritySettings.user_id == user_id)
            .first()
        )
        if settings:
            settings.last_login_at = datetime.utcnow()
            settings.last_login_ip = ip_address
            settings.failed_login_attempts = 0
            db.commit()

    @staticmethod
    def record_failed_login(db: Session, user_id: int) -> None:
        """Increment failed login counter; lock account after 10 consecutive failures."""
        settings = (
            db.query(SecuritySettings)
            .filter(SecuritySettings.user_id == user_id)
            .first()
        )
        if settings:
            settings.failed_login_attempts += 1
            if settings.failed_login_attempts >= 10:
                from datetime import timedelta
                settings.locked_until = datetime.utcnow() + timedelta(minutes=30)
            db.commit()
