"""Schemas for SecuritySettings."""

from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class SecuritySettingsResponse(BaseModel):
    """Public-safe view — never exposes the 2FA secret."""
    id: int
    user_id: int
    two_factor_enabled: bool
    two_factor_method: Optional[str]
    session_timeout_minutes: int
    last_login_at: Optional[datetime]
    last_login_ip: Optional[str]
    password_changed_at: datetime
    failed_login_attempts: int
    locked_until: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SecuritySettingsUpdate(BaseModel):
    """User-controllable fields (2FA toggling handled by dedicated endpoints)."""
    session_timeout_minutes: Optional[int] = None


class LoginRecordUpdate(BaseModel):
    """Internal schema used by auth service to record a successful login."""
    last_login_ip: Optional[str] = None
