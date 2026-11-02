from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.db.mixins import AuditMixin


class UserPost(Base, AuditMixin):
    __tablename__ = "user_posts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    linkedin_post_id = Column(String(128), nullable=True, index=True)
    content = Column(Text, nullable=False)
    posted_at = Column(DateTime, nullable=True)

    impressions = Column(Integer, nullable=True)
    likes = Column(Integer, nullable=True)
    comments = Column(Integer, nullable=True)
    reposts = Column(Integer, nullable=True)
    engagement_rate = Column(Float, nullable=True)

    topic = Column(String(100), nullable=True, index=True)
    post_format = Column(String(100), nullable=True, index=True)
    hook_type = Column(String(100), nullable=True)
    media_type = Column(String(100), nullable=True)

    user = relationship("User", back_populates="user_posts")

    def __repr__(self) -> str:
        return f"<UserPost(user_id={self.user_id}, id={self.id})>"
