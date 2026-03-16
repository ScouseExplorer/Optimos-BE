"""Chat schemas for request/response validation."""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ChatCreate(BaseModel):
    """Schema for creating a chat message."""
    user_message: str  # what user sends


class ChatResponse(BaseModel):
    """Response schema for a chat exchange."""
    id: int
    user_id: int
    user_message: str
    ai_response: str
    tokens_used: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatHistory(BaseModel):
    """Schema for chat history list."""
    chats: list[ChatResponse]
    total: int
    limit: int
    offset: int
