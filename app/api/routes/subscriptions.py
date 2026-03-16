"""Subscription routes for user subscription management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.auth.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.subscription import Subscription, SubscriptionUpdate, SubscriptionCreate
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


@router.get("/me", response_model=Subscription)
async def get_my_subscription(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's subscription."""
    subscription = SubscriptionService.get_or_create_subscription(db, current_user.id)
    return subscription


@router.post("/upgrade/{tier}")
async def upgrade_subscription(
    tier: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upgrade subscription tier (free, pro, enterprise)."""
    if tier not in ["free", "pro", "enterprise"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tier. Must be: free, pro, or enterprise"
        )
    
    subscription = SubscriptionService.upgrade_subscription(db, current_user.id, tier)
    return subscription


@router.get("/usage")
async def get_usage(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current usage statistics."""
    subscription = SubscriptionService.get_subscription(db, current_user.id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    remaining = subscription.messages_limit - subscription.messages_used
    return {
        "tier": subscription.tier,
        "messages_limit": subscription.messages_limit,
        "messages_used": subscription.messages_used,
        "messages_remaining": max(0, remaining),
        "usage_percentage": (subscription.messages_used / subscription.messages_limit * 100) if subscription.messages_limit > 0 else 0,
        "renews_at": subscription.renews_at,
    }
