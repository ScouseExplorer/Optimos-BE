"""SecuritySettings model — per-user security configuration and tracking."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.time import utcnow
from app.db.base import Base
from app.db.mixins import AuditMixin


class SecuritySettings(Base, AuditMixin):
    """Security configuration and login-tracking data for a user."""

    __tablename__ = "security_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Two-factor authentication
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    two_factor_method = Column(String(20), nullable=True)  # "totp" | "sms" | "email"
    two_factor_secret = Column(String(255), nullable=True)  # encrypted TOTP secret

    # Session management
    session_timeout_minutes = Column(Integer, default=10080, nullable=False)  # 7 days

    # Login tracking
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True)   # supports IPv6
    password_changed_at = Column(DateTime, default=utcnow, nullable=False)

    # Lockout tracking
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)  # null means not locked

    # Relationship
    user = relationship("User", back_populates="security_settings")

    def __repr__(self) -> str:
        return f"<SecuritySettings(user_id={self.user_id}, 2fa={self.two_factor_enabled})>"
