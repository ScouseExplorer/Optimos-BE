from sqlalchemy import JSON, Boolean, Column, Integer, String, Text, UniqueConstraint

from app.db.base import Base
from app.db.mixins import AuditMixin


class GlobalDatasetItem(Base, AuditMixin):
    __tablename__ = "global_dataset_items"
    __table_args__ = (
        UniqueConstraint("dataset_key", "item_key", name="uq_global_dataset_item_dataset_item"),
    )

    id = Column(Integer, primary_key=True, index=True)
    dataset_key = Column(String(100), nullable=False, index=True)
    item_key = Column(String(150), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(JSON, nullable=False, default=list)
    source = Column(String(255), nullable=True)
    priority = Column(Integer, nullable=False, default=0, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    def __repr__(self) -> str:
        return f"<GlobalDatasetItem(dataset_key={self.dataset_key}, item_key={self.item_key})>"
