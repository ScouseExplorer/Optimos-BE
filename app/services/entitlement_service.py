from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.subscription import Subscription
from app.services.credit_service import CreditService
from app.services.subscription_service import SubscriptionService


class EntitlementService:
    PLAN_FEATURES = {
        "free": {
            "generate_post",
            "basic_analytics",
        },
        "pro": {
            "generate_post",
            "basic_analytics",
            "deep_post_analysis",
            "personal_content_audit",
            "content_strategy",
        },
        "enterprise": {
            "generate_post",
            "basic_analytics",
            "deep_post_analysis",
            "personal_content_audit",
            "content_strategy",
            "historical_analysis",
            "competitor_analysis",
            "batch_generation",
            "deep_audience_analysis",
        },
    }

    @staticmethod
    def get_subscription(db: Session, user_id: int) -> Subscription | None:
        return SubscriptionService.get_subscription(db, user_id)

    @staticmethod
    def assert_feature_allowed(db: Session, user_id: int, feature_key: str) -> Subscription:
        sub = EntitlementService.get_subscription(db, user_id)
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Subscription required",
            )

        features = EntitlementService.PLAN_FEATURES.get(sub.tier, set())
        if sub.status != "active":
            features = set()
        if feature_key not in features:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Your current plan does not include '{feature_key}'",
            )
        return sub

    @staticmethod
    def get_user_entitlements(db: Session, user_id: int) -> dict:
        sub = EntitlementService.get_subscription(db, user_id)
        if not sub:
            return {
                "tier": "none",
                "status": "missing",
                "messages_limit": 0,
                "messages_used": 0,
                "features": [],
                "credit_balance": 0,
            }

        wallet = CreditService.get_or_create_wallet(db, user_id)
        features = EntitlementService.PLAN_FEATURES.get(sub.tier, set())
        if sub.status != "active":
            features = set()
        features = sorted(features)
        return {
            "tier": sub.tier,
            "status": sub.status,
            "messages_limit": sub.messages_limit,
            "messages_used": sub.messages_used,
            "messages_remaining": (
                max(0, sub.messages_limit - sub.messages_used)
                if sub.status == "active"
                else 0
            ),
            "features": features,
            "credit_balance": wallet.balance,
        }
