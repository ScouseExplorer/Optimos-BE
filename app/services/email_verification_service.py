"""Email verification and password reset service."""

from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import get_password_hash
from app.core.time import utcnow
from datetime import timedelta
import secrets
import logging

logger = logging.getLogger(__name__)


class EmailVerificationService:
    """Service for email verification and password reset."""
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def send_verification_token(db: Session, user_id: int) -> tuple[str, bool]:
        """Generate and save verification token for user."""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None, False
            
            token = EmailVerificationService.generate_token()
            user.email_verification_token = token
            db.commit()
            
            return token, True
        except Exception as e:
            logger.error(f"Failed to generate verification token: {str(e)}")
            return None, False
    
    @staticmethod
    def verify_email_token(db: Session, token: str) -> tuple[User, bool]:
        """Verify email using token."""
        try:
            user = db.query(User).filter(User.email_verification_token == token).first()
            if not user:
                logger.warning(
                    f"Email verification attempted with invalid token",
                    extra={"event": "email_verification_failed_invalid_token"}
                )
                return None, False
            
            user.is_email_verified = True
            user.email_verification_token = None  # Clear token after use
            db.commit()
            
            logger.info(
                f"Email verified successfully",
                extra={
                    "user_id": user.id,
                    "email": user.email,
                    "event": "email_verified"
                }
            )
            return user, True
        except Exception as e:
            logger.error(
                f"Email verification error: {str(e)}",
                extra={
                    "event": "email_verification_error",
                    "error": str(e)
                },
                exc_info=True
            )
            return None, False
    
    @staticmethod
    def send_password_reset_token(db: Session, email: str) -> tuple[str, bool]:
        """Generate and save password reset token."""
        try:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                # Don't reveal if email exists (security)
                return None, False
            
            token = EmailVerificationService.generate_token()
            user.password_reset_token = token
            user.password_reset_expires_at = utcnow() + timedelta(hours=1)
            db.commit()
            
            return token, True
        except Exception as e:
            logger.error(f"Failed to generate password reset token: {str(e)}")
            return None, False
    
    @staticmethod
    def reset_password_with_token(db: Session, token: str, new_password: str) -> tuple[User, bool]:
        """Reset password using token."""
        try:
            user = db.query(User).filter(User.password_reset_token == token).first()
            if not user:
                logger.warning(
                    f"Password reset attempted with invalid token",
                    extra={"event": "password_reset_failed_invalid_token"}
                )
                return None, False
            
            # Check if token expired
            if user.password_reset_expires_at < utcnow():
                user.password_reset_token = None
                user.password_reset_expires_at = None
                db.commit()
                logger.warning(
                    f"Password reset attempted with expired token",
                    extra={
                        "user_id": user.id,
                        "event": "password_reset_failed_expired_token"
                    }
                )
                return None, False
            
            # Update password
            user.hashed_password = get_password_hash(new_password)
            user.password_reset_token = None
            user.password_reset_expires_at = None
            db.commit()
            
            logger.info(
                f"Password reset successfully",
                extra={
                    "user_id": user.id,
                    "event": "password_reset_successful"
                }
            )
            return user, True
        except Exception as e:
            logger.error(
                f"Password reset error: {str(e)}",
                extra={
                    "event": "password_reset_error",
                    "error": str(e)
                },
                exc_info=True
            )
            return None, False
