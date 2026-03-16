"""Subscription service for managing user subscriptions."""

from sqlalchemy.orm import Session
from app.models.subscription import Subscription
from app.models.user import User
from datetime import datetime, timedelta


class SubscriptionService:
    """Service for subscription management."""
    
    @staticmethod
    def get_or_create_subscription(db: Session, user_id: int) -> Subscription:
        """Get subscription or create default for new user."""
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        if not subscription:
            subscription = Subscription(
                user_id=user_id,
                tier="free",
                status="active",
                messages_limit=100,
                renews_at=datetime.utcnow() + timedelta(days=30)
            )
            db.add(subscription)
            db.commit()
            db.refresh(subscription)
        return subscription
    
    @staticmethod
    def get_subscription(db: Session, user_id: int) -> Subscription:
        """Get user's subscription."""
        return db.query(Subscription).filter(Subscription.user_id == user_id).first()
    
    @staticmethod
    def upgrade_subscription(db: Session, user_id: int, tier: str) -> Subscription:
        """Upgrade user's subscription tier."""
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        if subscription:
            subscription.tier = tier
            # Update message limits based on tier
            if tier == "free":
                subscription.messages_limit = 100
            elif tier == "pro":
                subscription.messages_limit = 10000
            elif tier == "enterprise":
                subscription.messages_limit = 999999
            subscription.messages_used = 0  # Reset usage on upgrade
            subscription.renews_at = datetime.utcnow() + timedelta(days=30)
            db.commit()
            db.refresh(subscription)
        return subscription
    
    @staticmethod
    def check_message_limit(db: Session, user_id: int) -> bool:
        """Check if user has messages remaining."""
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        if not subscription:
            return False
        return subscription.messages_used < subscription.messages_limit
    
    @staticmethod
    def increment_message_usage(db: Session, user_id: int, tokens: int = 1) -> None:
        """Increment user's message usage."""
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        if subscription:
            subscription.messages_used += tokens
            db.commit()
    
    @staticmethod
    def reset_monthly_usage(db: Session) -> None:
        """Reset all users' monthly usage (run monthly)."""
        subscriptions = db.query(Subscription).all()
        for sub in subscriptions:
            sub.messages_used = 0
            sub.renews_at = datetime.utcnow() + timedelta(days=30)
        db.commit()
