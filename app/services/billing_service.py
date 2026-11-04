import hashlib
import hmac
import logging
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.billing_webhook_receipt import BillingWebhookReceipt
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.billing import PurchaseIntentRequest
from app.services.credit_service import CreditService
from app.services.subscription_service import SubscriptionService


logger = logging.getLogger(__name__)
STRIPE_API_BASE_URL = "https://api.stripe.com/v1"
STRIPE_SIGNATURE_TOLERANCE_SECONDS = 300


class BillingService:
    @staticmethod
    def create_purchase_intent(payload: PurchaseIntentRequest, user_id: int) -> dict:
        price_id = settings.STRIPE_CREDIT_PRICE_ID
        if not price_id:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stripe credit price is not configured",
            )

        success_url, cancel_url = BillingService._validated_return_urls(
            payload.success_url,
            payload.cancel_url,
        )
        return BillingService._create_checkout_session(
            {
                "mode": "payment",
                "line_items[0][price]": price_id,
                "line_items[0][quantity]": str(payload.credits),
                "success_url": success_url,
                "cancel_url": cancel_url,
                "client_reference_id": str(user_id),
                "metadata[user_id]": str(user_id),
                "metadata[purchase_type]": "credits",
                "metadata[credits]": str(payload.credits),
                "payment_intent_data[metadata][user_id]": str(user_id),
                "payment_intent_data[metadata][credits]": str(payload.credits),
            }
        )

    @staticmethod
    def create_subscription_intent(tier: str, user_id: int) -> dict:
        price_id = {
            "pro": settings.STRIPE_PRO_PRICE_ID,
            "enterprise": settings.STRIPE_ENTERPRISE_PRICE_ID,
        }.get(tier)
        if not price_id:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Stripe price for the {tier} plan is not configured",
            )

        success_url, cancel_url = BillingService._configured_return_urls()
        return BillingService._create_checkout_session(
            {
                "mode": "subscription",
                "line_items[0][price]": price_id,
                "line_items[0][quantity]": "1",
                "success_url": success_url,
                "cancel_url": cancel_url,
                "client_reference_id": str(user_id),
                "metadata[user_id]": str(user_id),
                "metadata[tier]": tier,
                "subscription_data[metadata][user_id]": str(user_id),
                "subscription_data[metadata][tier]": tier,
            }
        )

    @staticmethod
    def create_customer_portal(db: Session, user_id: int) -> dict:
        subscription = (
            db.query(Subscription)
            .filter(
                Subscription.user_id == user_id,
                Subscription.stripe_customer_id.is_not(None),
            )
            .first()
        )
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No Stripe billing account is associated with this user",
            )
        if not settings.STRIPE_SECRET_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stripe is not configured",
            )

        try:
            with httpx.Client(timeout=settings.MICROSERVICE_TIMEOUT_SECONDS) as client:
                response = client.post(
                    f"{STRIPE_API_BASE_URL}/billing_portal/sessions",
                    data={
                        "customer": subscription.stripe_customer_id,
                        "return_url": settings.FRONTEND_URL,
                    },
                    auth=(settings.STRIPE_SECRET_KEY, ""),
                )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Stripe billing portal creation failed: %s", exc.__class__.__name__)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Stripe billing portal creation failed",
            ) from exc

        if not isinstance(data, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Stripe returned an invalid billing portal response",
            )
        portal_url = data.get("url")
        if not isinstance(portal_url, str):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Stripe response is missing the billing portal URL",
            )
        return {"portal_url": portal_url}

    @staticmethod
    def _create_checkout_session(parameters: dict[str, str]) -> dict:
        if not settings.STRIPE_SECRET_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stripe is not configured",
            )

        try:
            with httpx.Client(timeout=settings.MICROSERVICE_TIMEOUT_SECONDS) as client:
                response = client.post(
                    f"{STRIPE_API_BASE_URL}/checkout/sessions",
                    data=parameters,
                    auth=(settings.STRIPE_SECRET_KEY, ""),
                )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Stripe checkout session creation failed: %s", exc.__class__.__name__)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Stripe checkout session creation failed",
            ) from exc

        if not isinstance(data, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Stripe returned an invalid checkout session",
            )
        checkout_url = data.get("url")
        session_id = data.get("id")
        if not isinstance(checkout_url, str) or not isinstance(session_id, str):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Stripe response is missing checkout session fields",
            )
        return {"checkout_url": checkout_url, "provider_intent_id": session_id}

    @staticmethod
    def _configured_return_urls() -> tuple[str, str]:
        if not settings.STRIPE_SUCCESS_URL or not settings.STRIPE_CANCEL_URL:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stripe return URLs are not configured",
            )
        return settings.STRIPE_SUCCESS_URL, settings.STRIPE_CANCEL_URL

    @staticmethod
    def _validated_return_urls(success_url: str, cancel_url: str) -> tuple[str, str]:
        frontend = urlparse(settings.FRONTEND_URL)
        for field_name, value in (("success_url", success_url), ("cancel_url", cancel_url)):
            parsed = urlparse(value)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.username
                or parsed.password
                or parsed.scheme != frontend.scheme
                or parsed.netloc != frontend.netloc
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{field_name} must use the configured frontend origin",
                )
        return success_url, cancel_url

    @staticmethod
    def verify_stripe_signature(payload: bytes, signature_header: str | None) -> bool:
        secret = settings.STRIPE_WEBHOOK_SECRET
        if not secret or not signature_header:
            return False

        fields: dict[str, list[str]] = {}
        for component in signature_header.split(","):
            key, separator, value = component.partition("=")
            if separator:
                fields.setdefault(key, []).append(value)

        timestamps = fields.get("t", [])
        signatures = fields.get("v1", [])
        if len(timestamps) != 1 or not signatures:
            return False

        try:
            timestamp = int(timestamps[0])
        except ValueError:
            return False
        if abs(int(time.time()) - timestamp) > STRIPE_SIGNATURE_TOLERANCE_SECONDS:
            return False

        signed_payload = str(timestamp).encode("ascii") + b"." + payload
        expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
        return any(hmac.compare_digest(expected, signature) for signature in signatures)

    @staticmethod
    async def apply_stripe_event(db: Session, event: dict) -> None:
        event_id = event.get("id")
        event_type = event.get("type")
        event_data = event.get("data")
        event_object = event_data.get("object") if isinstance(event_data, dict) else None
        if not isinstance(event_id, str) or not isinstance(event_type, str) or not isinstance(event_object, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed Stripe event",
            )

        if db.query(BillingWebhookReceipt).filter_by(provider_event_id=event_id).first():
            return

        if event_type in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
            if event_object.get("payment_status") != "paid":
                return
            if event_object.get("mode") == "payment":
                BillingService._apply_credit_checkout(db, event_object)
                return
            if event_object.get("mode") != "subscription":
                return
            subscription_id = BillingService._stripe_id(event_object.get("subscription"))
            if not subscription_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Stripe checkout event is missing its subscription",
                )
            subscription = await BillingService._retrieve_stripe_subscription(subscription_id)
            BillingService._sync_subscription(
                db,
                event_id,
                event_type,
                subscription,
                reset_usage=False,
                allow_tier_change=True,
            )
            return

        if event_type in {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        }:
            subscription_id = BillingService._stripe_id(event_object.get("id"))
            if not subscription_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Stripe subscription event is missing its subscription ID",
                )
            subscription = await BillingService._retrieve_stripe_subscription(subscription_id)
            BillingService._sync_subscription(
                db,
                event_id,
                event_type,
                subscription,
                reset_usage=False,
                allow_tier_change=False,
            )
            return

        if event_type in {"invoice.paid", "invoice.payment_failed"}:
            subscription_id = BillingService._invoice_subscription_id(event_object)
            if not subscription_id:
                return
            subscription = await BillingService._retrieve_stripe_subscription(subscription_id)
            BillingService._sync_subscription(
                db,
                event_id,
                event_type,
                subscription,
                reset_usage=event_object.get("billing_reason") == "subscription_cycle",
                allow_tier_change=event_type == "invoice.paid",
            )

    @staticmethod
    def _apply_credit_checkout(db: Session, checkout_session: dict) -> None:
        metadata = checkout_session.get("metadata")
        if not isinstance(metadata, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stripe credit checkout is missing valid purchase metadata",
            )
        if metadata.get("purchase_type") != "credits":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stripe checkout is not a credit purchase",
            )
        try:
            user_id = int(metadata["user_id"])
            credits = int(metadata["credits"])
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stripe credit checkout is missing valid purchase metadata",
            ) from exc

        reference_id = checkout_session.get("id")
        if not isinstance(reference_id, str) or not reference_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stripe credit checkout is missing its session ID",
            )
        CreditService.apply_billing_purchase(
            db=db,
            user_id=user_id,
            amount=credits,
            reference_id=reference_id,
            description="Stripe credit purchase",
        )

    @staticmethod
    async def _retrieve_stripe_subscription(subscription_id: str) -> dict:
        if not settings.STRIPE_SECRET_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stripe is not configured",
            )

        try:
            async with httpx.AsyncClient(timeout=settings.MICROSERVICE_TIMEOUT_SECONDS) as client:
                response = await client.get(
                    f"{STRIPE_API_BASE_URL}/subscriptions/{subscription_id}",
                    auth=(settings.STRIPE_SECRET_KEY, ""),
                )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Stripe subscription lookup failed: %s", exc.__class__.__name__)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to retrieve the Stripe subscription",
            ) from exc

        if not isinstance(data, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Stripe returned an invalid subscription",
            )
        return data

    @staticmethod
    def _sync_subscription(
        db: Session,
        event_id: str,
        event_type: str,
        stripe_subscription: dict,
        reset_usage: bool,
        allow_tier_change: bool,
    ) -> None:
        subscription_id = stripe_subscription.get("id")
        if not isinstance(subscription_id, str) or not subscription_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stripe subscription is missing its ID",
            )
        metadata = stripe_subscription.get("metadata")
        if not isinstance(metadata, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stripe subscription has invalid metadata",
            )
        raw_user_id = metadata.get("user_id")
        raw_tier = BillingService._subscription_tier(stripe_subscription, metadata)
        provider_status = stripe_subscription.get("status")

        try:
            user_id = int(raw_user_id)
        except (TypeError, ValueError):
            existing = db.query(Subscription).filter_by(
                stripe_subscription_id=subscription_id
            ).first()
            if existing is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Stripe subscription is missing valid user metadata",
                )
            user_id = existing.user_id

        if user_id is None or not db.query(User.id).filter(User.id == user_id).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stripe subscription refers to an unknown user",
            )

        valid_statuses = {
            "active",
            "trialing",
            "past_due",
            "unpaid",
            "canceled",
            "incomplete",
            "incomplete_expired",
            "paused",
        }
        if provider_status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stripe subscription has an invalid status",
            )

        if provider_status != "canceled" and raw_tier not in SubscriptionService.TIER_LIMITS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stripe subscription is missing a valid plan tier",
            )

        try:
            period_end = stripe_subscription.get("current_period_end")
            renews_at = (
                datetime.fromtimestamp(int(period_end), timezone.utc).replace(tzinfo=None)
                if period_end is not None
                else None
            )
        except (OverflowError, OSError, TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stripe subscription has an invalid billing period end",
            ) from exc

        now = datetime.utcnow()
        db.add(
            BillingWebhookReceipt(
                provider_event_id=event_id,
                event_type=event_type,
                processed_at=now,
            )
        )
        subscription = db.query(Subscription).filter_by(user_id=user_id).first()
        if subscription is None:
            subscription = Subscription(
                user_id=user_id,
                tier="free",
                status="active",
                messages_limit=SubscriptionService.TIER_LIMITS["free"],
                messages_used=0,
                usage_resets_at=now + timedelta(days=30),
            )
            db.add(subscription)

        previous_tier = subscription.tier
        subscription.stripe_subscription_id = subscription_id
        subscription.stripe_customer_id = BillingService._stripe_id(
            stripe_subscription.get("customer")
        )
        subscription.status = (
            "active"
            if provider_status in {"active", "trialing", "canceled"}
            else provider_status
        )
        subscription.renews_at = renews_at

        if provider_status == "canceled":
            subscription.tier = "free"
            subscription.messages_limit = SubscriptionService.TIER_LIMITS["free"]
            subscription.usage_resets_at = now + timedelta(days=30)
            subscription.cancelled_at = now
        elif allow_tier_change:
            if provider_status in {"active", "trialing"}:
                subscription.cancelled_at = None
            subscription.tier = raw_tier
            subscription.messages_limit = SubscriptionService.TIER_LIMITS[raw_tier]
            if previous_tier != raw_tier and provider_status in {"active", "trialing"}:
                subscription.messages_used = 0
                subscription.usage_resets_at = now + timedelta(days=30)
            elif reset_usage and provider_status in {"active", "trialing"}:
                subscription.messages_used = 0
                subscription.usage_resets_at = now + timedelta(days=30)

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            if db.query(BillingWebhookReceipt).filter_by(provider_event_id=event_id).first():
                return
            raise

    @staticmethod
    def _subscription_tier(stripe_subscription: dict, metadata: dict) -> str | None:
        configured_prices = {
            settings.STRIPE_PRO_PRICE_ID: "pro",
            settings.STRIPE_ENTERPRISE_PRICE_ID: "enterprise",
        }
        configured_prices = {price_id: tier for price_id, tier in configured_prices.items() if price_id}
        items = stripe_subscription.get("items")
        item_data = items.get("data", []) if isinstance(items, dict) else []
        for item in item_data:
            if not isinstance(item, dict):
                continue
            price = item.get("price") or {}
            if not isinstance(price, dict):
                continue
            tier = configured_prices.get(price.get("id"))
            if tier:
                return tier
        if configured_prices:
            return None
        return metadata.get("tier")

    @staticmethod
    def _stripe_id(value) -> str | None:
        if isinstance(value, str):
            return value
        if isinstance(value, dict) and isinstance(value.get("id"), str):
            return value["id"]
        return None

    @staticmethod
    def _invoice_subscription_id(invoice: dict) -> str | None:
        direct = BillingService._stripe_id(invoice.get("subscription"))
        if direct:
            return direct
        parent = invoice.get("parent")
        details = parent.get("subscription_details") if isinstance(parent, dict) else None
        if not isinstance(details, dict):
            return None
        return BillingService._stripe_id(details.get("subscription"))
