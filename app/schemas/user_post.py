from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserPostCreate(BaseModel):
    linkedin_post_id: str | None = None
    content: str
    posted_at: datetime | None = None
    impressions: int | None = None
    likes: int | None = None
    comments: int | None = None
    reposts: int | None = None
    engagement_rate: float | None = None
    topic: str | None = None
    post_format: str | None = None
    hook_type: str | None = None
    media_type: str | None = None


class UserPostUpdate(BaseModel):
    content: str | None = None
    posted_at: datetime | None = None
    impressions: int | None = None
    likes: int | None = None
    comments: int | None = None
    reposts: int | None = None
    engagement_rate: float | None = None
    topic: str | None = None
    post_format: str | None = None
    hook_type: str | None = None
    media_type: str | None = None


class UserPostResponse(BaseModel):
    id: int
    user_id: int
    linkedin_post_id: str | None = None
    content: str
    posted_at: datetime | None = None
    impressions: int | None = None
    likes: int | None = None
    comments: int | None = None
    reposts: int | None = None
    engagement_rate: float | None = None
    topic: str | None = None
    post_format: str | None = None
    hook_type: str | None = None
    media_type: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
