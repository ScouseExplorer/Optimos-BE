from sqlalchemy import Column, ForeignKey, Float, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.db.mixins import AuditMixin


class AIUsage(Base, AuditMixin):
    __tablename__ = "ai_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String(128), nullable=False, index=True)
    model = Column(String(128), nullable=False)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    estimated_cost = Column(Float, nullable=True)
    credits_charged = Column(Integer, nullable=False, default=0)
    request_id = Column(String(128), nullable=True, index=True)
    status = Column(String(32), nullable=False, default="success", index=True)
    error_message = Column(Text, nullable=True)

    user = relationship("User", back_populates="ai_usage_entries")

    def __repr__(self) -> str:
        return f"<AIUsage(user_id={self.user_id}, action={self.action}, status={self.status})>"
