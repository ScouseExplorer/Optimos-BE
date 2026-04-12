from typing import Optional
import logging
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, User
from app.core.security import get_password_hash, verify_password
from app.models.user import User as UserModel

logger = logging.getLogger(__name__)


class UserService:
    """Service class for user business logic."""
    
    async def get_user_by_email(self, db: Session, email: str) -> Optional[UserModel]:
        """Get user by email from database."""
        return db.query(UserModel).filter(UserModel.email == email).first()
    
    async def get_user_by_id(self, db: Session, user_id: int) -> Optional[UserModel]:
        """Get user by ID from database."""
        return db.query(UserModel).filter(UserModel.id == user_id).first()
    
    async def create_user(self, db: Session, user_data: UserCreate) -> User:
        """Create a new user in the database."""
        try:
            # Hash the password
            hashed_password = get_password_hash(user_data.password)
            
            # Create user object
            user_in_db = UserModel(
                email=user_data.email,
                username=user_data.username,
                hashed_password=hashed_password,
                is_active=True
            )
            
            # Save to database
            db.add(user_in_db)
            db.commit()
            db.refresh(user_in_db)
            
            logger.info(
                f"User created successfully",
                extra={
                    "user_id": user_in_db.id,
                    "email": user_data.email,
                    "username": user_data.username,
                    "event": "user_created"
                }
            )
            
            # Return user without password hash
            return User(
                id=user_in_db.id,
                email=user_in_db.email,
                username=user_in_db.username,
                is_active=user_in_db.is_active
            )
        except Exception as e:
            logger.error(
                f"Failed to create user: {str(e)}",
                extra={
                    "email": user_data.email,
                    "username": user_data.username,
                    "event": "user_creation_failed",
                    "error": str(e)
                },
                exc_info=True
            )
            raise
    
    async def get_user_by_username(self, db: Session, username: str) -> Optional[UserModel]:
        """Get user by username from database."""
        return db.query(UserModel).filter(UserModel.username == username).first()
    
    async def authenticate_user(self, db: Session, username: str, password: str) -> Optional[UserModel]:
        """Authenticate a user with username and password."""
        try:
            user = await self.get_user_by_username(db, username)
            if not user:
                logger.warning(
                    f"Login attempt with non-existent username",
                    extra={
                        "username": username,
                        "event": "login_failed_user_not_found"
                    }
                )
                return None
            if not verify_password(password, user.hashed_password):
                logger.warning(
                    f"Login attempt with wrong password",
                    extra={
                        "user_id": user.id,
                        "username": username,
                        "event": "login_failed_wrong_password"
                    }
                )
                return None
            
            logger.info(
                f"User authenticated successfully",
                extra={
                    "user_id": user.id,
                    "username": username,
                    "event": "user_authenticated"
                }
            )
            return user
        except Exception as e:
            logger.error(
                f"Authentication error: {str(e)}",
                extra={
                    "username": username,
                    "event": "authentication_error",
                    "error": str(e)
                },
                exc_info=True
            )
            raise
    
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
            is_active=db_user.is_active
        )
    
    async def delete_user(self, db: Session, user_id: int) -> bool:
        """Delete a user."""
        db_user = await self.get_user_by_id(db, user_id)
        if not db_user:
            return False
        db.delete(db_user)
        db.commit()
        return True
