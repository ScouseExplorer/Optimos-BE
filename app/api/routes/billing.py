import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.billing import BillingWebhookEvent, PurchaseIntentRequest, PurchaseIntentResponse
from app.services.billing_service import BillingService


router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.post("/purchase-intent", response_model=PurchaseIntentResponse)
async def create_purchase_intent(
    payload: PurchaseIntentRequest,
    current_user: User = Depends(get_current_active_user),
):
    data = BillingService.create_purchase_intent(payload, current_user.id)
    return PurchaseIntentResponse(**data)


@router.post("/webhooks", status_code=status.HTTP_202_ACCEPTED)
async def handle_billing_webhook(
    event: BillingWebhookEvent,
    x_billing_token: str | None = Header(default=None, alias="X-Billing-Token"),
    db: Session = Depends(get_db),
):
    if not settings.BILLING_WEBHOOK_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing webhook token is not configured",
        )
    # Trust boundary: this is an internal event from the billing service, which must
    # verify the Stripe signature (STRIPE_WEBHOOK_SECRET) before calling this route.
    if not x_billing_token or not hmac.compare_digest(
        x_billing_token.encode(), settings.BILLING_WEBHOOK_TOKEN.encode()
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid billing webhook token")

    BillingService.apply_webhook_credit_event(db, event)
    return {"status": "accepted"}
