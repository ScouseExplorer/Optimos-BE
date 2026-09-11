"""NotificationPreferences model — per-user notification toggles."""

from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.mixins import AuditMixin


class NotificationPreferences(Base, AuditMixin):
    """Stores which notifications a user wants to receive."""

    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Email notifications
    email_new_message = Column(Boolean, default=True, nullable=False)      # AI response ready
    email_billing = Column(Boolean, default=True, nullable=False)           # billing events
    email_security = Column(Boolean, default=True, nullable=False)          # login / security alerts
    email_product_updates = Column(Boolean, default=False, nullable=False)  # newsletter
    email_weekly_summary = Column(Boolean, default=True, nullable=False)    # weekly usage digest

    # Push / in-app notifications
    push_enabled = Column(Boolean, default=True, nullable=False)
    push_new_message = Column(Boolean, default=True, nullable=False)
    push_billing = Column(Boolean, default=True, nullable=False)

    # Relationship
    user = relationship("User", back_populates="notification_preferences")

    def __repr__(self) -> str:
        return f"<NotificationPreferences(user_id={self.user_id})>"
