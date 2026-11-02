from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.db.mixins import AuditMixin


class CreditWallet(Base, AuditMixin):
    __tablename__ = "credit_wallets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    balance = Column(Integer, nullable=False, default=0)

    user = relationship("User", back_populates="credit_wallet")

    def __repr__(self) -> str:
        return f"<CreditWallet(user_id={self.user_id}, balance={self.balance})>"
