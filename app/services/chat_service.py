"""Chat service for managing user chats."""

from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.chat import Chat
from app.models.subscription import Subscription


class ChatService:
    """Service for chat management."""
    
    @staticmethod
    def create_chat(
        db: Session,
        user_id: int,
        user_message: str,
        ai_response: str,
        tokens_used: int = 0
    ) -> Chat:
        """Create a new chat message."""
        # Get user's subscription
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        if not subscription:
            raise ValueError("User subscription not found")
        
        chat = Chat(
            user_id=user_id,
            subscription_id=subscription.id,
            user_message=user_message,
            ai_response=ai_response,
            tokens_used=tokens_used
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)
        return chat
    
    @staticmethod
    def get_chat_history(db: Session, user_id: int, limit: int = 50, offset: int = 0) -> tuple:
        """Get chat history for user (paginated)."""
        query = db.query(Chat).filter(Chat.user_id == user_id).order_by(desc(Chat.created_at))
        total = query.count()
        chats = query.limit(limit).offset(offset).all()
        return chats, total
    
    @staticmethod
    def get_chat_by_id(db: Session, chat_id: int, user_id: int) -> Chat:
        """Get specific chat message (check ownership)."""
        return db.query(Chat).filter(
            Chat.id == chat_id,
            Chat.user_id == user_id
        ).first()
    
    @staticmethod
    def delete_chat(db: Session, chat_id: int, user_id: int) -> bool:
        """Delete chat message (check ownership)."""
        chat = db.query(Chat).filter(
            Chat.id == chat_id,
            Chat.user_id == user_id
        ).first()
        if chat:
            db.delete(chat)
            db.commit()
            return True
        return False
    
    @staticmethod
    def delete_all_chats(db: Session, user_id: int) -> int:
        """Delete all chats for user."""
        count = db.query(Chat).filter(Chat.user_id == user_id).delete()
        db.commit()
        return count
