from datetime import timedelta

from app.core.time import utcnow
from sqlalchemy.orm import Session

from app.models.feature_cost import FeatureCost
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.billing import PurchaseIntentRequest
from conftest import post_signed_stripe_event


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register_and_login(client, email: str, username: str, password: str = "Pass12345!"):
    register = client.post(
        "/api/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    assert register.status_code == 201
    confirm_registered_email(client, email)
    user = register.json()

    login = client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return user, token


def promote_to_admin(db_session_factory, user_id: int) -> None:
    db: Session = db_session_factory()
    try:
        row = db.query(User).filter(User.id == user_id).first()
        row.is_admin = True
        db.commit()
    finally:
        db.close()


def set_feature_cost(db_session_factory, feature_key: str, amount: int) -> None:
    db: Session = db_session_factory()
    try:
        row = db.query(FeatureCost).filter(FeatureCost.feature_key == feature_key).first()
        if not row:
            row = FeatureCost(
                feature_key=feature_key,
                credit_cost=amount,
                is_active=True,
            )
            db.add(row)
        else:
            row.credit_cost = amount
            row.is_active = True
        db.commit()
    finally:
        db.close()


def test_stripe_credit_webhook_replay_is_idempotent(client, monkeypatch):
    user, token = register_and_login(client, "billreplay@example.com", "bill_replay_user")

    from app.core.config import settings

    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test")
    event = {
        "id": "evt_credit_replay_1",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_credit_replay_1",
                "mode": "payment",
                "payment_status": "paid",
                "metadata": {
                    "purchase_type": "credits",
                    "user_id": str(user["id"]),
                    "credits": "30",
                },
            }
        },
    }

    first = post_signed_stripe_event(client, event, "whsec_test")
    second = post_signed_stripe_event(client, event, "whsec_test")

    assert first.status_code == 202
    assert second.status_code == 202

    wallet = client.get("/api/credits/wallet", headers=auth_headers(token))
    assert wallet.status_code == 200
    assert wallet.json()["balance"] == 30

    transactions = client.get("/api/credits/transactions", headers=auth_headers(token))
    assert transactions.status_code == 200
    billing_rows = [
        row
        for row in transactions.json()["items"]
        if row["transaction_type"] == "BILLING_PURCHASE" and row["reference_id"] == "cs_credit_replay_1"
    ]
    assert len(billing_rows) == 1


def test_stripe_webhook_rejects_untrusted_callers(client, monkeypatch):
    user, _ = register_and_login(client, "billauth@example.com", "bill_auth_user")

    from app.core.config import settings

    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", None)
    unconfigured = client.post("/api/billing/webhooks", json={})
    assert unconfigured.status_code == 503

    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test")
    unsigned = client.post("/api/billing/webhooks", json={})
    invalid = client.post(
        "/api/billing/webhooks",
        headers={"Stripe-Signature": "t=1,v1=invalid"},
        json={},
    )
    assert unsigned.status_code == 400
    assert invalid.status_code == 400

    assert user["id"] > 0


def test_credit_checkout_uses_configured_price_and_frontend_redirects(monkeypatch):
    from app.core.config import settings
    from app.services.billing_service import BillingService

    monkeypatch.setattr(settings, "STRIPE_CREDIT_PRICE_ID", "price_credit_unit")
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://app.example.com")
    captured = {}
    monkeypatch.setattr(
        BillingService,
        "_create_checkout_session",
        staticmethod(lambda parameters: captured.update(parameters) or {
            "checkout_url": "https://checkout.stripe.com/session",
            "provider_intent_id": "cs_credit_test",
        }),
    )

    result = BillingService.create_purchase_intent(
        PurchaseIntentRequest(
            credits=25,
            success_url="https://app.example.com/billing/success",
            cancel_url="https://app.example.com/billing/cancel",
        ),
        user_id=42,
    )

    assert result["provider_intent_id"] == "cs_credit_test"
    assert captured["mode"] == "payment"
    assert captured["line_items[0][price]"] == "price_credit_unit"
    assert captured["line_items[0][quantity]"] == "25"
    assert captured["metadata[user_id]"] == "42"


def _subscription_checkout_event(event_id: str, subscription_id: str = "sub_test_1") -> dict:
    return {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_subscription_1",
                "mode": "subscription",
                "payment_status": "paid",
                "subscription": subscription_id,
            }
        },
    }


def test_stripe_subscription_events_update_paid_tier(client, monkeypatch):
    user, token = register_and_login(client, "tierchg@example.com", "tier_change_user")

    from app.core.config import settings
    from app.services.billing_service import BillingService

    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setattr(settings, "ALLOW_SELF_SERVICE_TIER_CHANGE", False)
    stripe_subscription = {
        "id": "sub_test_1",
        "customer": "cus_test_1",
        "status": "active",
        "current_period_end": 1_800_000_000,
        "metadata": {"user_id": str(user["id"]), "tier": "pro"},
    }
    async def retrieve_subscription(_subscription_id):
        return stripe_subscription.copy()

    monkeypatch.setattr(
        BillingService,
        "_retrieve_stripe_subscription",
        staticmethod(retrieve_subscription),
    )

    # Users cannot grant themselves a paid plan.
    assert client.post("/api/subscriptions/upgrade/pro", headers=auth_headers(token)).status_code == 403

    def entitlements():
        r = client.get("/api/subscriptions/entitlements", headers=auth_headers(token))
        assert r.status_code == 200
        return r.json()

    assert entitlements()["tier"] == "free"

    first = post_signed_stripe_event(
        client,
        _subscription_checkout_event("evt_sub_pro"),
        "whsec_test",
    )
    assert first.status_code == 202
    pro = entitlements()
    assert pro["tier"] == "pro"
    assert pro["messages_limit"] == 10000
    assert "competitor_analysis" not in pro["features"]
    duplicate_checkout = client.post(
        "/api/billing/subscription-intent",
        headers=auth_headers(token),
        json={"tier": "enterprise"},
    )
    assert duplicate_checkout.status_code == 409

    stripe_subscription["metadata"]["tier"] = "enterprise"
    enterprise = post_signed_stripe_event(
        client,
        {
            "id": "evt_sub_enterprise",
            "type": "invoice.paid",
            "data": {
                "object": {
                    "subscription": "sub_test_1",
                    "billing_reason": "subscription_update",
                }
            },
        },
        "whsec_test",
    )
    assert enterprise.status_code == 202
    top = entitlements()
    assert top["tier"] == "enterprise"
    assert top["messages_limit"] == 999999
    assert "competitor_analysis" in top["features"]

    # Replay does not reset usage or change state.
    usage_before = top["messages_used"]
    assert post_signed_stripe_event(
        client,
        {
            "id": "evt_sub_enterprise",
            "type": "invoice.paid",
            "data": {
                "object": {
                    "subscription": "sub_test_1",
                    "billing_reason": "subscription_update",
                }
            },
        },
        "whsec_test",
    ).status_code == 202
    assert entitlements()["messages_used"] == usage_before

    # A failed payment disables premium features until Stripe reports recovery.
    stripe_subscription["status"] = "past_due"
    failed = post_signed_stripe_event(
        client,
        {
            "id": "evt_invoice_failed",
            "type": "invoice.payment_failed",
            "data": {"object": {"subscription": "sub_test_1"}},
        },
        "whsec_test",
    )
    assert failed.status_code == 202
    current = entitlements()
    assert current["tier"] == "enterprise"
    assert current["status"] == "past_due"
    assert current["features"] == []

    stripe_subscription["status"] = "canceled"
    canceled = post_signed_stripe_event(
        client,
        {
            "id": "evt_sub_canceled",
            "type": "customer.subscription.deleted",
            "data": {"object": {"id": "sub_test_1"}},
        },
        "whsec_test",
    )
    assert canceled.status_code == 202
    free = entitlements()
    assert free["tier"] == "free"
    assert free["status"] == "active"


def test_stripe_subscription_checkout_uses_configured_plan_price(client, monkeypatch):
    user, token = register_and_login(client, "stripecheckout@example.com", "stripe_checkout_user")

    from app.core.config import settings
    from app.services import billing_service

    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_key")
    monkeypatch.setattr(settings, "STRIPE_PRO_PRICE_ID", "price_pro_monthly")
    monkeypatch.setattr(settings, "STRIPE_SUCCESS_URL", "https://app.example.com/success")
    monkeypatch.setattr(settings, "STRIPE_CANCEL_URL", "https://app.example.com/cancel")

    requests = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        @staticmethod
        def json():
            return {"id": "cs_test_checkout", "url": "https://checkout.stripe.com/session"}

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, url, data, auth):
            requests.append({"url": url, "data": data, "auth": auth})
            return FakeResponse()

    monkeypatch.setattr(billing_service.httpx, "Client", FakeClient)
    response = client.post(
        "/api/billing/subscription-intent",
        headers=auth_headers(token),
        json={"tier": "pro"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "checkout_url": "https://checkout.stripe.com/session",
        "provider_intent_id": "cs_test_checkout",
    }
    assert requests[0]["url"].endswith("/checkout/sessions")
    assert requests[0]["data"]["mode"] == "subscription"
    assert requests[0]["data"]["line_items[0][price]"] == "price_pro_monthly"
    assert requests[0]["data"]["subscription_data[metadata][user_id]"] == str(user["id"])


def test_paid_subscription_quota_resets_only_after_successful_renewal(client, monkeypatch, db_session_factory):
    user, token = register_and_login(client, "renewal@example.com", "renewal_user")

    from app.core.config import settings
    from app.services.billing_service import BillingService

    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test")
    stripe_subscription = {
        "id": "sub_renewal_1",
        "customer": "cus_renewal_1",
        "status": "active",
        "current_period_end": 1_800_000_000,
        "metadata": {"user_id": str(user["id"]), "tier": "pro"},
    }
    async def retrieve_subscription(_subscription_id):
        return stripe_subscription.copy()

    monkeypatch.setattr(
        BillingService,
        "_retrieve_stripe_subscription",
        staticmethod(retrieve_subscription),
    )

    created = post_signed_stripe_event(
        client,
        _subscription_checkout_event("evt_renewal_created", "sub_renewal_1"),
        "whsec_test",
    )
    assert created.status_code == 202

    db = db_session_factory()
    try:
        subscription = db.query(Subscription).filter_by(user_id=user["id"]).one()
        subscription.messages_used = 42
        subscription.usage_resets_at = utcnow() - timedelta(days=1)
        db.commit()
    finally:
        db.close()

    usage = client.get("/api/subscriptions/usage", headers=auth_headers(token))
    assert usage.status_code == 200
    assert usage.json()["messages_used"] == 42

    invoice = {
        "id": "evt_invoice_cycle_1",
        "type": "invoice.paid",
        "data": {
            "object": {
                "subscription": "sub_renewal_1",
                "billing_reason": "subscription_cycle",
            }
        },
    }
    assert post_signed_stripe_event(client, invoice, "whsec_test").status_code == 202
    renewed = client.get("/api/subscriptions/usage", headers=auth_headers(token))
    assert renewed.json()["messages_used"] == 0

    db = db_session_factory()
    try:
        subscription = db.query(Subscription).filter_by(user_id=user["id"]).one()
        subscription.messages_used = 3
        db.commit()
    finally:
        db.close()

    assert post_signed_stripe_event(client, invoice, "whsec_test").status_code == 202
    replayed = client.get("/api/subscriptions/usage", headers=auth_headers(token))
    assert replayed.json()["messages_used"] == 3


def test_free_subscription_quota_renews_on_30_day_period(client, db_session_factory):
    user, token = register_and_login(client, "freequota@example.com", "free_quota_user")
    db = db_session_factory()
    try:
        subscription = db.query(Subscription).filter_by(user_id=user["id"]).one()
        subscription.messages_used = subscription.messages_limit
        subscription.usage_resets_at = utcnow() - timedelta(days=31)
        db.commit()
    finally:
        db.close()

    response = client.get("/api/subscriptions/usage", headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json()["messages_used"] == 0
    assert response.json()["messages_remaining"] == response.json()["messages_limit"]


def test_post_analysis_requires_entitlement_and_credits(client, db_session_factory):
    user, token = register_and_login(client, "analysisgate@example.com", "analysis_gate_user")
    admin_user, admin_token = register_and_login(client, "analysisadmin@example.com", "analysis_admin_user")
    promote_to_admin(db_session_factory, admin_user["id"])

    created = client.post(
        "/api/posts",
        headers=auth_headers(token),
        json={"content": "How we improved onboarding by 27%?", "topic": "product"},
    )
    assert created.status_code == 201
    post_id = created.json()["id"]

    # free tier should not have deep_post_analysis entitlement.
    blocked_for_tier = client.post(
        f"/api/posts/{post_id}/analyze",
        headers=auth_headers(token),
        json={"save_to_post": False},
    )
    assert blocked_for_tier.status_code == 403

    upgrade = client.post(
        "/api/subscriptions/upgrade/pro",
        headers=auth_headers(token),
    )
    assert upgrade.status_code == 200

    set_feature_cost(db_session_factory, "deep_post_analysis", 5)

    # No credits yet, should be payment required.
    blocked_for_credits = client.post(
        f"/api/posts/{post_id}/analyze",
        headers=auth_headers(token),
        json={"save_to_post": False},
    )
    assert blocked_for_credits.status_code == 402

    top_up = client.post(
        "/api/credits/admin/adjust",
        headers=auth_headers(admin_token),
        json={"user_id": user["id"], "amount": 10, "description": "analysis credits"},
    )
    assert top_up.status_code == 201

    allowed = client.post(
        f"/api/posts/{post_id}/analyze",
        headers={**auth_headers(token), "Idempotency-Key": "analyze-1"},
        json={"save_to_post": True},
    )
    assert allowed.status_code == 200
    assert allowed.json()["provider"] in {"local-fallback", "post-analysis-service"}

    wallet = client.get("/api/credits/wallet", headers=auth_headers(token))
    assert wallet.status_code == 200
    assert wallet.json()["balance"] == 5

    transactions = client.get("/api/credits/transactions", headers=auth_headers(token))
    assert transactions.status_code == 200
    reservation_rows = [
        row
        for row in transactions.json()["items"]
        if row["transaction_type"] == "RESERVATION" and row["source"] == "deep_post_analysis"
    ]
    assert reservation_rows
    assert reservation_rows[0]["status"] == "settled"


def test_purchase_then_spend_to_zero_then_lockout(client, monkeypatch):
    from app.core.config import settings

    user, token = register_and_login(client, "spenddown@example.com", "spenddown_user")

    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test")

    upgrade = client.post("/api/subscriptions/upgrade/pro", headers=auth_headers(token))
    assert upgrade.status_code == 200

    seeded_post = client.post(
        "/api/posts",
        headers=auth_headers(token),
        json={"content": "How we improved onboarding by 27%?", "topic": "product"},
    )
    assert seeded_post.status_code == 201
    post_id = seeded_post.json()["id"]

    purchase = post_signed_stripe_event(
        client,
        {
            "id": "evt_spenddown_1",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_spenddown_1",
                    "mode": "payment",
                    "payment_status": "paid",
                    "metadata": {
                        "purchase_type": "credits",
                        "user_id": str(user["id"]),
                        "credits": "15",
                    },
                }
            },
        },
        "whsec_test",
    )
    assert purchase.status_code == 202

    chat = client.post(
        "/api/chats",
        headers={**auth_headers(token), "Idempotency-Key": "spend-chat-1"},
        json={"user_message": "Draft one practical post idea from my profile"},
    )
    assert chat.status_code == 200

    analysis = client.post(
        f"/api/posts/{post_id}/analyze",
        headers={**auth_headers(token), "Idempotency-Key": "spend-analyze-1"},
        json={"save_to_post": False},
    )
    assert analysis.status_code == 200

    wallet = client.get("/api/credits/wallet", headers=auth_headers(token))
    assert wallet.status_code == 200
    assert wallet.json()["balance"] == 0

    locked = client.post(
        "/api/chats",
        headers={**auth_headers(token), "Idempotency-Key": "spend-chat-2"},
        json={"user_message": "Give me one more idea"},
    )
    assert locked.status_code == 402
from conftest import confirm_registered_email
