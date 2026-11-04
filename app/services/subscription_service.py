"""Subscription service for managing user subscriptions."""

from sqlalchemy.orm import Session
from app.models.subscription import Subscription
from app.core.time import utcnow
from datetime import datetime, timedelta


class SubscriptionService:
    """Service for subscription management."""
    
    @staticmethod
    def get_or_create_subscription(db: Session, user_id: int) -> Subscription:
        """Get subscription or create default for new user."""
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        if not subscription:
            now = utcnow()
            subscription = Subscription(
                user_id=user_id,
                tier="free",
                status="active",
                messages_limit=100,
                renews_at=now + timedelta(days=30),
                usage_resets_at=now + timedelta(days=30),
            )
            db.add(subscription)
            db.commit()
            db.refresh(subscription)
        else:
            SubscriptionService._reset_due_free_usage(db, subscription)
        return subscription
    
    @staticmethod
    def get_subscription(db: Session, user_id: int) -> Subscription | None:
        """Get user's subscription."""
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        if subscription:
            SubscriptionService._reset_due_free_usage(db, subscription)
        return subscription

    TIER_LIMITS = {"free": 100, "pro": 10000, "enterprise": 999999}

    @staticmethod
    def _reset_due_free_usage(
        db: Session,
        subscription: Subscription,
        now: datetime | None = None,
    ) -> None:
        """Renew free-tier usage lazily while preserving the original 30-day cadence."""
        now = now or utcnow()
        if subscription.tier != "free" or subscription.status != "active":
            return

        reset_at = subscription.usage_resets_at or subscription.renews_at
        if reset_at is None:
            subscription.usage_resets_at = now + timedelta(days=30)
            db.commit()
            return

        if reset_at > now:
            return

        periods_elapsed = (now - reset_at) // timedelta(days=30) + 1
        subscription.messages_used = 0
        subscription.usage_resets_at = reset_at + periods_elapsed * timedelta(days=30)
        subscription.renews_at = subscription.usage_resets_at
        db.commit()

    @staticmethod
    def upgrade_subscription(db: Session, user_id: int, tier: str) -> Subscription:
        """Upgrade user's subscription tier."""
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        if subscription:
            now = utcnow()
            subscription.tier = tier
            subscription.status = "active"
            subscription.messages_limit = SubscriptionService.TIER_LIMITS[tier]
            subscription.messages_used = 0  # Reset usage on upgrade
            subscription.renews_at = now + timedelta(days=30)
            subscription.usage_resets_at = now + timedelta(days=30)
            db.commit()
            db.refresh(subscription)
        return subscription

    @staticmethod
    def set_tier(db: Session, user_id: int, tier: str) -> Subscription:
        """Apply a paid tier change. Idempotent: replaying the same tier is a no-op."""
        subscription = SubscriptionService.get_or_create_subscription(db, user_id)
        if subscription.tier == tier and subscription.status == "active":
            return subscription
        return SubscriptionService.upgrade_subscription(db, user_id, tier)
    
    @staticmethod
    def check_message_limit(db: Session, user_id: int) -> bool:
        """Check if user has messages remaining."""
        subscription = SubscriptionService.get_subscription(db, user_id)
        if not subscription:
            return False
        if subscription.status != "active":
            return False
        return subscription.messages_used < subscription.messages_limit
    
    @staticmethod
    def increment_message_usage(db: Session, user_id: int, tokens: int = 1) -> None:
        """Increment user's message usage."""
        subscription = SubscriptionService.get_subscription(db, user_id)
        if subscription:
            subscription.messages_used += tokens
            db.commit()
    
    @staticmethod
    def reset_monthly_usage(db: Session) -> None:
        """Reset due free-tier quotas; paid quotas renew only after verified payment."""
        subscriptions = (
            db.query(Subscription)
            .filter(Subscription.tier == "free", Subscription.status == "active")
            .all()
        )
        for subscription in subscriptions:
            SubscriptionService._reset_due_free_usage(db, subscription)
