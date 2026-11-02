from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base
from app.db.mixins import AuditMixin


class User(Base, AuditMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    email_verified_at = Column(DateTime, nullable=True)
    auth_version = Column(Integer, default=0, nullable=False)

    # Relationships
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    chats = relationship("Chat", back_populates="user")
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    notification_preferences = relationship(
        "NotificationPreferences", back_populates="user", uselist=False
    )
    security_settings = relationship("SecuritySettings", back_populates="user", uselist=False)
    credit_wallet = relationship("CreditWallet", back_populates="user", uselist=False)
    credit_transactions = relationship("CreditTransaction", back_populates="user")
    ai_usage_entries = relationship("AIUsage", back_populates="user")
    experiences = relationship("Experience", back_populates="user")
    opinions = relationship("Opinion", back_populates="user")
    user_posts = relationship("UserPost", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"