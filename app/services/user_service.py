import logging
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, User
from app.core.security import get_password_hash, verify_password
from app.models.user import User as UserModel
from app.models.subscription import Subscription
from app.models.profile import UserProfile
from app.models.notification_preferences import NotificationPreferences
from app.models.security_settings import SecuritySettings
from app.models.credit_wallet import CreditWallet
from app.core.time import utcnow
from datetime import timedelta

logger = logging.getLogger(__name__)


class UserService:
    """Service class for user business logic."""
    
    async def get_user_by_email(self, db: Session, email: str) -> Optional[UserModel]:
        """Get user by email from database."""
        return db.query(UserModel).filter(func.lower(UserModel.email) == email.lower()).first()
    
    async def get_user_by_id(self, db: Session, user_id: int) -> Optional[UserModel]:
        """Get user by ID from database."""
        return db.query(UserModel).filter(UserModel.id == user_id).first()
    
    async def create_user(self, db: Session, user_data: UserCreate) -> User:
        """Create a new user in the database."""
        # Hash the password
        hashed_password = get_password_hash(user_data.password)
        
        # Create user object
        user_in_db = UserModel(
            email=user_data.email,
            username=user_data.username,
            hashed_password=hashed_password,
            is_active=False,
        )
        
        # Save to database
        db.add(user_in_db)
        db.flush()  # get user_in_db.id before committing

        # Create default free subscription for new user
        subscription = Subscription(
            user_id=user_in_db.id,
            tier="free",
            status="active",
            messages_limit=100,
            messages_used=0,
            renews_at=utcnow() + timedelta(days=30),
        )
        db.add(subscription)

        # Create default profile
        db.add(UserProfile(user_id=user_in_db.id))

        # Create default notification preferences
        db.add(NotificationPreferences(user_id=user_in_db.id))

        # Create default security settings
        db.add(SecuritySettings(user_id=user_in_db.id))

        # Create default credit wallet
        db.add(CreditWallet(user_id=user_in_db.id, balance=0))

        db.commit()
        db.refresh(user_in_db)

        # Return user without password hash
        return User(
            id=user_in_db.id,
            email=user_in_db.email,
            username=user_in_db.username,
            is_active=user_in_db.is_active,
            email_verified_at=user_in_db.email_verified_at,
        )
    
    async def get_user_by_username(self, db: Session, username: str) -> Optional[UserModel]:
        """Get user by username from database."""
        return db.query(UserModel).filter(UserModel.username == username).first()

    async def get_user_by_username_or_email(self, db: Session, login: str) -> Optional[UserModel]:
        """Look up a user by username OR email (case-sensitive)."""
        return (
            db.query(UserModel)
            .filter(or_(UserModel.username == login, UserModel.email == login))
            .first()
        )

    async def authenticate_user(self, db: Session, username_or_email: str, password: str) -> Optional[UserModel]:
        """Authenticate a user by username or email.

        Raises HTTP 423 if the account is locked.
        Returns None if credentials are wrong (and records the failed attempt).
        """
        user = await self.get_user_by_username_or_email(db, username_or_email)
        if not user:
            return None

        # Enforce account lockout before touching the password
        security = db.query(SecuritySettings).filter(SecuritySettings.user_id == user.id).first()
        if security and security.locked_until and security.locked_until > utcnow():
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account temporarily locked due to too many failed attempts. Try again in 30 minutes.",
            )

        if not verify_password(password, user.hashed_password):
            # Record failed attempt and potentially lock the account
            if security:
                security.failed_login_attempts += 1
                if security.failed_login_attempts >= 10:
                    security.locked_until = utcnow() + timedelta(minutes=30)
                db.commit()
            return None

        return user
    
    async def update_user(self, db: Session, user_id: int, user_data: dict) -> Optional[User]:
        """Update user information."""
        db_user = await self.get_user_by_id(db, user_id)
        if not db_user:
            return None
        for key, value in user_data.items():
            if hasattr(db_user, key):
                setattr(db_user, key, value)
        db.commit()
        db.refresh(db_user)
        return User(
            id=db_user.id,
            email=db_user.email,
            username=db_user.username,
            is_active=db_user.is_active,
            email_verified_at=db_user.email_verified_at,
        )
    
    async def delete_user(self, db: Session, user_id: int) -> bool:
        """Delete a user."""
        db_user = await self.get_user_by_id(db, user_id)
        if not db_user:
            return False
        db.delete(db_user)
        db.commit()
        return True
