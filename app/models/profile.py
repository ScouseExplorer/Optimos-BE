"""UserProfile model — extended user information."""

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.db.mixins import AuditMixin


class UserProfile(Base, AuditMixin):
    """Extended profile information for a user."""

    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    display_name = Column(String(150), nullable=True)  # shown in UI; falls back to username
    bio = Column(String(500), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    phone = Column(String(30), nullable=True)
    timezone = Column(String(50), nullable=False, default="UTC")
    language = Column(String(10), nullable=False, default="en")

    # Relationship back to user
    user = relationship("User", back_populates="profile")

    def __repr__(self) -> str:
        return f"<UserProfile(user_id={self.user_id}, display_name={self.display_name})>"
