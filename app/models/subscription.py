"""Subscription model for user tiers and billing."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base
from app.db.mixins import AuditMixin


class Subscription(Base, AuditMixin):
    """User subscription plan and tier information."""
    
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    tier = Column(String, default="free", index=True)  # free, pro, enterprise
    status = Column(String, default="active", index=True)  # active, cancelled, expired
    messages_limit = Column(Integer, default=100)  # monthly message limit
    messages_used = Column(Integer, default=0)  # current month usage
    renews_at = Column(DateTime, nullable=True, index=True)  # next billing date
    usage_resets_at = Column(DateTime, nullable=True, index=True)
    cancelled_at = Column(DateTime, nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True, unique=True, index=True)
    stripe_customer_id = Column(String(255), nullable=True, index=True)
    
    # Relationship
    user = relationship("User", back_populates="subscription")
    chats = relationship("Chat", back_populates="subscription")
    
    def __repr__(self):
        return f"<Subscription(user_id={self.user_id}, tier={self.tier}, status={self.status})>"
