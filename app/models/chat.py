"""Chat/Message model for storing conversation history."""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base
from app.db.mixins import AuditMixin


class Chat(Base, AuditMixin):
    """Chat message history between user and AI."""
    
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False, index=True)
    user_message = Column(Text, nullable=False)  # what user sent
    ai_response = Column(Text, nullable=False)  # what AI replied
    tokens_used = Column(Integer, default=0)  # for tracking usage
    
    # Relationships
    user = relationship("User", back_populates="chats")
    subscription = relationship("Subscription", back_populates="chats")
    
    def __repr__(self):
        return f"<Chat(user_id={self.user_id}, created_at={self.created_at})>"
