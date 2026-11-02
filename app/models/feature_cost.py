from sqlalchemy import Boolean, Column, Integer, String

from app.db.base import Base
from app.db.mixins import AuditMixin


class FeatureCost(Base, AuditMixin):
    __tablename__ = "feature_costs"

    id = Column(Integer, primary_key=True, index=True)
    feature_key = Column(String(128), nullable=False, unique=True, index=True)
    credit_cost = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<FeatureCost(feature_key={self.feature_key}, credit_cost={self.credit_cost})>"
