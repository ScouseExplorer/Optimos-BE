from sqlalchemy.orm import Session

from app.models.feature_cost import FeatureCost
from app.models.user import User


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


def test_billing_webhook_replay_is_idempotent(client, monkeypatch):
    user, token = register_and_login(client, "billreplay@example.com", "bill_replay_user")

    from app.core.config import settings

    monkeypatch.setattr(settings, "BILLING_WEBHOOK_TOKEN", "billing-token")

    payload = {
        "event_type": "credits.purchased",
        "user_id": user["id"],
        "credits": 30,
        "reference_id": "intent_replay_1",
        "description": "Purchase completed",
    }

    first = client.post(
        "/api/billing/webhooks",
        headers={"X-Billing-Token": "billing-token"},
        json=payload,
    )
    second = client.post(
        "/api/billing/webhooks",
        headers={"X-Billing-Token": "billing-token"},
        json=payload,
    )

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
        if row["transaction_type"] == "BILLING_PURCHASE" and row["reference_id"] == "intent_replay_1"
    ]
    assert len(billing_rows) == 1


def test_billing_webhook_rejects_untrusted_callers(client, monkeypatch):
    user, token = register_and_login(client, "billauth@example.com", "bill_auth_user")

    from app.core.config import settings

    payload = {
        "event_type": "credits.purchased",
        "user_id": user["id"],
        "credits": 50,
        "reference_id": "intent_untrusted_1",
    }

    monkeypatch.setattr(settings, "BILLING_WEBHOOK_TOKEN", None)
    unconfigured = client.post(
        "/api/billing/webhooks", headers={"X-Billing-Token": "anything"}, json=payload
    )
    assert unconfigured.status_code == 503

    monkeypatch.setattr(settings, "BILLING_WEBHOOK_TOKEN", "billing-token")
    missing = client.post("/api/billing/webhooks", json=payload)
    wrong = client.post("/api/billing/webhooks", headers={"X-Billing-Token": "nope"}, json=payload)
    user_jwt = client.post("/api/billing/webhooks", headers=auth_headers(token), json=payload)
    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert user_jwt.status_code == 401

    wallet = client.get("/api/credits/wallet", headers=auth_headers(token))
    assert wallet.json()["balance"] == 0


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

    monkeypatch.setattr(settings, "BILLING_WEBHOOK_TOKEN", "billing-token")

    upgrade = client.post("/api/subscriptions/upgrade/pro", headers=auth_headers(token))
    assert upgrade.status_code == 200

    seeded_post = client.post(
        "/api/posts",
        headers=auth_headers(token),
        json={"content": "How we improved onboarding by 27%?", "topic": "product"},
    )
    assert seeded_post.status_code == 201
    post_id = seeded_post.json()["id"]

    purchase = client.post(
        "/api/billing/webhooks",
        headers={"X-Billing-Token": "billing-token"},
        json={
            "event_type": "credits.purchased",
            "user_id": user["id"],
            "credits": 15,
            "reference_id": "intent_spenddown_1",
            "description": "Purchase completed",
        },
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
