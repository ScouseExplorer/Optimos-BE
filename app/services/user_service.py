from typing import Optional
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, User, UserInDB
from app.core.security import get_password_hash, verify_password
from app.models.user import User as UserModel


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
        
        # Return user without password hash
        return User(
            id=user_in_db.id,
            email=user_in_db.email,
            username=user_in_db.username,
            is_active=user_in_db.is_active
        )
    
    async def get_user_by_username(self, db: Session, username: str) -> Optional[UserModel]:
        """Get user by username from database."""
        return db.query(UserModel).filter(UserModel.username == username).first()
    
    async def authenticate_user(self, db: Session, username: str, password: str) -> Optional[UserModel]:
        """Authenticate a user with username and password."""
        user = await self.get_user_by_username(db, username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
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
