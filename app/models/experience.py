from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.db.mixins import AuditMixin


class Experience(Base, AuditMixin):
    __tablename__ = "experiences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=True, index=True)
    experience_date = Column(DateTime, nullable=True)
    importance = Column(Integer, nullable=False, default=3)

    user = relationship("User", back_populates="experiences")

    def __repr__(self) -> str:
        return f"<Experience(user_id={self.user_id}, title={self.title})>"
