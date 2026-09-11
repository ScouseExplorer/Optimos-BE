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

    # Relationships
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    chats = relationship("Chat", back_populates="user")
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    notification_preferences = relationship(
        "NotificationPreferences", back_populates="user", uselist=False
    )
    security_settings = relationship("SecuritySettings", back_populates="user", uselist=False)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"