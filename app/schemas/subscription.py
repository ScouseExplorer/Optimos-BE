"""Subscription schemas for request/response validation."""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class SubscriptionCreate(BaseModel):
    """Schema for creating a subscription."""
    tier: str = "free"  # free, pro, enterprise
    messages_limit: int = 100


class Subscription(BaseModel):
    """Response schema for subscription."""
    id: int
    user_id: int
    tier: str
    status: str
    messages_limit: int
    messages_used: int
    created_at: datetime
    renews_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class SubscriptionUpdate(BaseModel):
    """Schema for updating subscription."""
    tier: Optional[str] = None
    status: Optional[str] = None
    messages_limit: Optional[int] = None
    messages_used: Optional[int] = None
    renews_at: Optional[datetime] = None
