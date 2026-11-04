"""Subscription routes for user subscription management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import get_db
from app.auth.dependencies import get_current_active_user
from app.models.user import User
from app.models.subscription import Subscription as SubscriptionModel
from app.schemas.subscription import Subscription, SubscriptionUpdate, SubscriptionCreate
from app.services.entitlement_service import EntitlementService
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
    
    if tier != "free" and not settings.ALLOW_SELF_SERVICE_TIER_CHANGE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Paid plan changes require completed payment",
        )

    stripe_subscription = (
        db.query(SubscriptionModel)
        .filter(
            SubscriptionModel.user_id == current_user.id,
            SubscriptionModel.stripe_subscription_id.is_not(None),
            SubscriptionModel.tier != "free",
            SubscriptionModel.status.notin_(["canceled", "expired"]),
        )
        .first()
    )
    if stripe_subscription:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Manage Stripe subscription changes through the billing portal",
        )

    SubscriptionService.get_or_create_subscription(db, current_user.id)
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
        "messages_remaining": max(0, remaining) if subscription.status == "active" else 0,
        "usage_percentage": (subscription.messages_used / subscription.messages_limit * 100) if subscription.messages_limit > 0 else 0,
        "renews_at": subscription.renews_at,
        "usage_resets_at": subscription.usage_resets_at,
    }


@router.get("/entitlements")
async def get_entitlements(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get explicit entitlement contract for frontend rendering."""
    return EntitlementService.get_user_entitlements(db, current_user.id)
