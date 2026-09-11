"""Schemas for NotificationPreferences."""

from pydantic import BaseModel
from datetime import datetime


class NotificationPreferencesBase(BaseModel):
    email_new_message: bool = True
    email_billing: bool = True
    email_security: bool = True
    email_product_updates: bool = False
    email_weekly_summary: bool = True
    push_enabled: bool = True
    push_new_message: bool = True
    push_billing: bool = True


class NotificationPreferencesUpdate(BaseModel):
    """All fields are optional for partial updates."""
    email_new_message: bool | None = None
    email_billing: bool | None = None
    email_security: bool | None = None
    email_product_updates: bool | None = None
    email_weekly_summary: bool | None = None
    push_enabled: bool | None = None
    push_new_message: bool | None = None
    push_billing: bool | None = None


class NotificationPreferencesResponse(NotificationPreferencesBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
