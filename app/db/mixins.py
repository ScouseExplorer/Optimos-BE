"""SQLAlchemy audit mixin — adds created_at, updated_at, updated_by to any model."""

from datetime import datetime
from sqlalchemy import Column, DateTime, Integer


class AuditMixin:
    """Mixin that adds standard audit timestamp columns to a model."""

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    # ID of the user who last modified this row (null = system/self)
    updated_by = Column(Integer, nullable=True)
