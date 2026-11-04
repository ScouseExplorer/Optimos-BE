"""SQLAlchemy audit mixin — adds created_at, updated_at, updated_by to any model."""

from sqlalchemy import Column, DateTime, Integer

from app.core.time import utcnow


class AuditMixin:
    """Mixin that adds standard audit timestamp columns to a model."""

    created_at = Column(DateTime, default=utcnow, nullable=False, index=True)
    updated_at = Column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )
    # ID of the user who last modified this row (null = system/self)
    updated_by = Column(Integer, nullable=True)
