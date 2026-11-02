from sqlalchemy import Column, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.db.mixins import AuditMixin


class CreditTransaction(Base, AuditMixin):
    __tablename__ = "credit_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Integer, nullable=False)
    transaction_type = Column(String(64), nullable=False, index=True)
    source = Column(String(128), nullable=False, index=True)
    reference_id = Column(String(128), nullable=True, index=True)
    request_id = Column(String(128), nullable=True, index=True)
    status = Column(String(32), nullable=False, default="settled", index=True)
    description = Column(Text, nullable=True)

    user = relationship("User", back_populates="credit_transactions")

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "request_id",
            "transaction_type",
            name="uq_credit_tx_user_request_type",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<CreditTransaction(user_id={self.user_id}, amount={self.amount}, "
            f"type={self.transaction_type}, status={self.status})>"
        )
