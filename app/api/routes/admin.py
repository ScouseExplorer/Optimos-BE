"""Admin routes for dashboard and analytics."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from app.core.time import utcnow
from app.db.session import get_db
from app.auth.dependencies import get_current_active_user
from app.models.user import User
from app.models.subscription import Subscription
from app.models.chat import Chat
from pydantic import BaseModel, ConfigDict

router = APIRouter(prefix="/api/admin", tags=["admin"])


class DashboardStats(BaseModel):
    """Dashboard statistics."""
    total_users: int
    total_signups_today: int
    active_subscriptions: int
    total_messages: int
    monthly_recurring_revenue: float
    free_users: int
    pro_users: int
    enterprise_users: int
    

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics (admin only)."""
    # Check admin status
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    # Total users
    total_users = db.query(func.count(User.id)).scalar()
    
    # Signups today
    today_start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    signups_today = db.query(func.count(User.id)).filter(
        User.created_at >= today_start
    ).scalar()
    
    # Active subscriptions
    active_subs = db.query(func.count(Subscription.id)).filter(
        Subscription.status == "active"
    ).scalar()
    
    # Total messages
    total_messages = db.query(func.count(Chat.id)).scalar()
    
    # MRR Calculation (assuming Pro = $29, Enterprise = $99)
    tiers = db.query(
        Subscription.tier,
        func.count(Subscription.id).label("count")
    ).filter(Subscription.status == "active").group_by(Subscription.tier).all()
    
    mrr = 0.0
    free_count = 0
    pro_count = 0
    enterprise_count = 0
    
    for tier, count in tiers:
        if tier == "pro":
            mrr += count * 29
            pro_count = count
        elif tier == "enterprise":
            mrr += count * 99
            enterprise_count = count
        elif tier == "free":
            free_count = count
    
    return DashboardStats(
        total_users=total_users or 0,
        total_signups_today=signups_today or 0,
        active_subscriptions=active_subs or 0,
        total_messages=total_messages or 0,
        monthly_recurring_revenue=mrr,
        free_users=free_count,
        pro_users=pro_count,
        enterprise_users=enterprise_count
    )


class UserDetail(BaseModel):
    """User detail for listing."""
    id: int
    email: str
    username: str
    tier: str
    status: str
    messages_used: int
    messages_limit: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


@router.get("/users", response_model=list[UserDetail])
async def get_all_users(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get all users with subscription details (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    users = db.query(User).all()
    
    result = []
    for user in users:
        sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
        if sub:
            result.append(UserDetail(
                id=user.id,
                email=user.email,
                username=user.username,
                tier=sub.tier,
                status=sub.status,
                messages_used=sub.messages_used,
                messages_limit=sub.messages_limit,
                created_at=user.created_at
            ))
    
    return result


class ChatStats(BaseModel):
    """Chat statistics."""
    date: datetime
    message_count: int
    active_users: int


@router.get("/chat-stats", response_model=list[ChatStats])
async def get_chat_stats(
    days: int = 7,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get chat activity stats for last N days (admin only)."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    stats = []
    for i in range(days):
        date = utcnow() - timedelta(days=i)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)
        
        message_count = db.query(func.count(Chat.id)).filter(
            and_(Chat.created_at >= date_start, Chat.created_at < date_end)
        ).scalar()
        
        active_users = db.query(func.count(func.distinct(Chat.user_id))).filter(
            and_(Chat.created_at >= date_start, Chat.created_at < date_end)
        ).scalar()
        
        stats.append(ChatStats(
            date=date_start,
            message_count=message_count or 0,
            active_users=active_users or 0
        ))
    
    return stats
