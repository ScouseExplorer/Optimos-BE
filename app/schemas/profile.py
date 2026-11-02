"""Schemas for UserProfile."""

from pydantic import BaseModel, ConfigDict, HttpUrl
from typing import Optional
from datetime import datetime


class ProfileBase(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    timezone: Optional[str] = "UTC"
    language: Optional[str] = "en"


class ProfileUpdate(ProfileBase):
    """Fields that can be updated by the user."""
    pass


class ProfileResponse(ProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
