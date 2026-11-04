from sqlalchemy import Column, DateTime, Integer, String

from app.db.base import Base


class BillingWebhookReceipt(Base):
    __tablename__ = "billing_webhook_receipts"

    id = Column(Integer, primary_key=True)
    provider_event_id = Column(String(255), nullable=False, unique=True, index=True)
    event_type = Column(String(100), nullable=False)
    processed_at = Column(DateTime, nullable=False)
