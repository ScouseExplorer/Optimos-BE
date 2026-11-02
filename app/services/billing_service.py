from fastapi import HTTPException, status
import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.schemas.billing import BillingWebhookEvent, PurchaseIntentRequest
from app.services.credit_service import CreditService


class BillingService:
    @staticmethod
    def create_purchase_intent(payload: PurchaseIntentRequest, user_id: int) -> dict:
        if not settings.BILLING_SERVICE_URL:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Billing service URL is not configured",
            )

        url = f"{settings.BILLING_SERVICE_URL.rstrip('/')}/purchase-intents"
        body = {
            "user_id": user_id,
            "credits": payload.credits,
            "success_url": payload.success_url,
            "cancel_url": payload.cancel_url,
        }

        try:
            with httpx.Client(timeout=settings.MICROSERVICE_TIMEOUT_SECONDS) as client:
                response = client.post(url, json=body)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Billing service request failed: {exc}",
            ) from exc

        data = response.json()
        checkout_url = data.get("checkout_url")
        provider_intent_id = data.get("provider_intent_id")
        if not checkout_url or not provider_intent_id:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Billing service response missing required fields",
            )
        return {
            "checkout_url": checkout_url,
            "provider_intent_id": provider_intent_id,
        }

    @staticmethod
    def apply_webhook_credit_event(db: Session, event: BillingWebhookEvent) -> None:
        if event.event_type != "credits.purchased":
            return

        if not event.reference_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Billing webhook event is missing reference_id",
            )

        CreditService.apply_billing_purchase(
            db=db,
            user_id=event.user_id,
            amount=event.credits,
            reference_id=event.reference_id,
            description=event.description or "Webhook credits purchase",
        )
