"""Chat routes for user chat interactions."""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.auth.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.chat import ChatCreate, ChatResponse, ChatHistory
from app.services.chat_service import ChatService
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/api/chats", tags=["chats"])


@router.post("", response_model=ChatResponse)
async def send_message(
    chat_input: ChatCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Send a message to AI chatbot and get response."""
    # Check message limit
    if not SubscriptionService.check_message_limit(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Message limit reached for this month"
        )
    
    # TODO: Call your AI service/API here
    # For now, we'll create a mock response
    ai_response = f"Echo: {chat_input.user_message}"
    
    # Create chat record
    chat = ChatService.create_chat(
        db=db,
        user_id=current_user.id,
        user_message=chat_input.user_message,
        ai_response=ai_response,
        tokens_used=len(chat_input.user_message.split())
    )
    
    # Increment usage
    SubscriptionService.increment_message_usage(db, current_user.id, tokens=1)
    
    return chat


@router.get("", response_model=ChatHistory)
async def get_chats(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's chat history."""
    chats, total = ChatService.get_chat_history(db, current_user.id, limit, offset)
    return ChatHistory(
        chats=chats,
        total=total,
        limit=limit,
        offset=offset
    )


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    chat_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a specific chat message."""
    success = ChatService.delete_chat(db, chat_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    return None


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_all_chats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete all user chats."""
    ChatService.delete_all_chats(db, current_user.id)
    return None
