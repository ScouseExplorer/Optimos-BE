import hashlib
import secrets
from datetime import datetime, timedelta
from urllib.parse import quote

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.auth_action_token import AuthActionToken
from app.models.security_settings import SecuritySettings
from app.models.user import User
from app.services.email_service import email_service


class AuthActionService:
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    async def _issue_token(
        db: Session,
        user: User,
        purpose: str,
        lifetime: timedelta,
        subject: str,
        path: str,
    ) -> None:
        now = datetime.utcnow()
        token = secrets.token_urlsafe(32)
        db.query(AuthActionToken).filter(
            AuthActionToken.user_id == user.id,
            AuthActionToken.purpose == purpose,
            AuthActionToken.used_at.is_(None),
        ).update({"used_at": now}, synchronize_session=False)
        db.add(
            AuthActionToken(
                user_id=user.id,
                purpose=purpose,
                token_hash=AuthActionService._hash_token(token),
                expires_at=now + lifetime,
            )
        )
        db.commit()

        url = f"{settings.FRONTEND_URL.rstrip('/')}/{path}?token={quote(token, safe='')}"
        await email_service.send_email(
            recipient=user.email,
            subject=subject,
            html=f'<p>Continue by <a href="{url}">opening this link</a>.</p>',
            text=f"Continue by opening this link: {url}",
        )

    @staticmethod
    async def send_verification(db: Session, user: User) -> None:
        await AuthActionService._issue_token(
            db=db,
            user=user,
            purpose=AuthActionService.EMAIL_VERIFICATION,
            lifetime=timedelta(hours=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS),
            subject="Verify your Optimos email address",
            path="verify-email",
        )

    @staticmethod
    async def send_password_reset(db: Session, user: User) -> None:
        await AuthActionService._issue_token(
            db=db,
            user=user,
            purpose=AuthActionService.PASSWORD_RESET,
            lifetime=timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
            subject="Reset your Optimos password",
            path="reset-password",
        )

    @staticmethod
    def consume_email_verification(db: Session, token: str) -> bool:
        now = datetime.utcnow()
        token_hash = AuthActionService._hash_token(token)
        action = (
            db.query(AuthActionToken)
            .filter(
                AuthActionToken.token_hash == token_hash,
                AuthActionToken.purpose == AuthActionService.EMAIL_VERIFICATION,
                AuthActionToken.used_at.is_(None),
                AuthActionToken.expires_at > now,
            )
            .first()
        )
        if action is None:
            return False

        consumed = db.execute(
            update(AuthActionToken)
            .where(
                AuthActionToken.id == action.id,
                AuthActionToken.used_at.is_(None),
                AuthActionToken.expires_at > now,
            )
            .values(used_at=now)
        )
        if consumed.rowcount != 1:
            db.rollback()
            return False

        user = db.query(User).filter(User.id == action.user_id).first()
        if user is None:
            db.rollback()
            return False

        user.email_verified_at = now
        user.is_active = True
        db.query(AuthActionToken).filter(
            AuthActionToken.user_id == user.id,
            AuthActionToken.purpose == AuthActionService.EMAIL_VERIFICATION,
            AuthActionToken.used_at.is_(None),
        ).update({"used_at": now}, synchronize_session=False)
        db.commit()
        return True

    @staticmethod
    def reset_password(db: Session, token: str, password: str) -> bool:
        now = datetime.utcnow()
        token_hash = AuthActionService._hash_token(token)
        action = (
            db.query(AuthActionToken)
            .filter(
                AuthActionToken.token_hash == token_hash,
                AuthActionToken.purpose == AuthActionService.PASSWORD_RESET,
                AuthActionToken.used_at.is_(None),
                AuthActionToken.expires_at > now,
            )
            .first()
        )
        if action is None:
            return False

        consumed = db.execute(
            update(AuthActionToken)
            .where(
                AuthActionToken.id == action.id,
                AuthActionToken.used_at.is_(None),
                AuthActionToken.expires_at > now,
            )
            .values(used_at=now)
        )
        if consumed.rowcount != 1:
            db.rollback()
            return False

        user = db.query(User).filter(User.id == action.user_id).first()
        if user is None:
            db.rollback()
            return False

        user.hashed_password = get_password_hash(password)
        user.auth_version += 1
        security = db.query(SecuritySettings).filter(SecuritySettings.user_id == user.id).first()
        if security:
            security.password_changed_at = now
        db.query(AuthActionToken).filter(
            AuthActionToken.user_id == user.id,
            AuthActionToken.used_at.is_(None),
        ).update({"used_at": now}, synchronize_session=False)
        db.commit()
        return True
