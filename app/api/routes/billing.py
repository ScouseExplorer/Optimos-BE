from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.models.subscription import Subscription
from app.schemas.billing import (
    CustomerPortalResponse,
    PurchaseIntentRequest,
    PurchaseIntentResponse,
    SubscriptionIntentRequest,
)
from app.services.billing_service import BillingService


router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.post("/purchase-intent", response_model=PurchaseIntentResponse)
def create_purchase_intent(
    payload: PurchaseIntentRequest,
    current_user: User = Depends(get_current_active_user),
):
    data = BillingService.create_purchase_intent(payload, current_user.id)
    return PurchaseIntentResponse(**data)


@router.post("/subscription-intent", response_model=PurchaseIntentResponse)
def create_subscription_intent(
    payload: SubscriptionIntentRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == current_user.id,
            Subscription.stripe_subscription_id.is_not(None),
            Subscription.tier != "free",
            Subscription.status.notin_(["canceled", "expired"]),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active paid subscription already exists; use the billing portal to manage it",
        )
    data = BillingService.create_subscription_intent(payload.tier, current_user.id)
    return PurchaseIntentResponse(**data)


@router.post("/customer-portal", response_model=CustomerPortalResponse)
def create_customer_portal(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return BillingService.create_customer_portal(db, current_user.id)


@router.post("/webhooks", status_code=status.HTTP_202_ACCEPTED)
@router.post("/stripe-webhooks", status_code=status.HTTP_202_ACCEPTED, include_in_schema=False)
async def handle_billing_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe webhook secret is not configured",
        )
    raw_body = await request.body()
    if not BillingService.verify_stripe_signature(raw_body, stripe_signature):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Stripe signature")

    try:
        event = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Stripe event JSON") from exc
    if not isinstance(event, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Stripe event payload")

    await BillingService.apply_stripe_event(db, event)
    return {"status": "accepted"}
