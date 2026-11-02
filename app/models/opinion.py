from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.db.mixins import AuditMixin


class Opinion(Base, AuditMixin):
    __tablename__ = "opinions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    topic = Column(String(200), nullable=False, index=True)
    opinion = Column(Text, nullable=False)
    confidence = Column(Integer, nullable=True)

    user = relationship("User", back_populates="opinions")

    def __repr__(self) -> str:
        return f"<Opinion(user_id={self.user_id}, topic={self.topic})>"
