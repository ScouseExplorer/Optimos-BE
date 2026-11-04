from app.core.config import settings
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.ai.generation_service import GenerationService
from app.services.billing_service import BillingService
from app.services.post_analysis_service import PostAnalysisService
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

    login = client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
    )
    assert login.status_code == 200
    return register.json(), login.json()["access_token"]


def promote_to_admin(db_session_factory, user_id: int) -> None:
    db: Session = db_session_factory()
    try:
        row = db.query(User).filter(User.id == user_id).first()
        row.is_admin = True
        db.commit()
    finally:
        db.close()


def top_up_user_credits(client, db_session_factory, user_id: int, amount: int = 50) -> None:
    admin_user, admin_token = register_and_login(client, "ms-admin@example.com", "ms_admin_user")
    promote_to_admin(db_session_factory, admin_user["id"])

    response = client.post(
        "/api/credits/admin/adjust",
        headers=auth_headers(admin_token),
        json={"user_id": user_id, "amount": amount, "description": "test top-up"},
    )
    assert response.status_code == 201


def test_chat_uses_remote_ai_service_url(client, monkeypatch, db_session_factory):
    user, token = register_and_login(client, "ms-ai@example.com", "ms_ai_user")
    top_up_user_credits(client, db_session_factory, user["id"], amount=20)

    def fake_generate_remote(context: dict) -> dict:
        assert context.get("user_prompt")
        return {
            "model": "remote-gpt",
            "text": "Remote AI response from url service",
            "input_tokens": 12,
            "output_tokens": 24,
            "estimated_cost": 0.002,
        }

    monkeypatch.setattr(settings, "AI_SERVICE_URL", "http://ai-svc.local")
    monkeypatch.setattr(GenerationService, "_generate_remote", staticmethod(fake_generate_remote))

    headers = auth_headers(token)
    headers["Idempotency-Key"] = "remote-ai-flow"
    response = client.post(
        "/api/chats",
        headers=headers,
        json={"user_message": "Draft a post from my recent wins"},
    )

    assert response.status_code == 200
    assert response.json()["ai_response"] == "Remote AI response from url service"


def test_post_analysis_uses_remote_service_and_saves_fields(client, monkeypatch, db_session_factory):
    user, token = register_and_login(client, "ms-an@example.com", "ms_an_user")
    upgrade = client.post("/api/subscriptions/upgrade/pro", headers=auth_headers(token))
    assert upgrade.status_code == 200
    top_up_user_credits(client, db_session_factory, user["id"], amount=20)

    def fake_analyze_remote(content: str) -> dict:
        assert "onboarding" in content.lower()
        return {
            "provider": "post-analysis-service",
            "summary": "Strong practical framing with clear CTA",
            "topic": "product",
            "post_format": "structured",
            "hook_type": "question",
            "media_type": "text",
            "confidence": 0.93,
        }

    monkeypatch.setattr(settings, "POST_ANALYSIS_SERVICE_URL", "http://analysis-svc.local")
    monkeypatch.setattr(PostAnalysisService, "_analyze_remote", staticmethod(fake_analyze_remote))

    created = client.post(
        "/api/posts",
        headers=auth_headers(token),
        json={"content": "How we improved onboarding by 27%?", "topic": "unknown"},
    )
    assert created.status_code == 201
    post_id = created.json()["id"]

    analysis = client.post(
        f"/api/posts/{post_id}/analyze",
        headers=auth_headers(token),
        json={"save_to_post": True},
    )
    assert analysis.status_code == 200
    assert analysis.json()["provider"] == "post-analysis-service"
    assert analysis.json()["topic"] == "product"

    posts = client.get("/api/posts", headers=auth_headers(token))
    assert posts.status_code == 200
    assert posts.json()["items"][0]["topic"] == "product"
    assert posts.json()["items"][0]["hook_type"] == "question"


def test_billing_purchase_intent_and_webhook_via_urls(client, monkeypatch):
    user, token = register_and_login(client, "ms-bill@example.com", "ms_bill_user")

    def fake_create_purchase_intent(payload, user_id: int) -> dict:
        assert user_id == user["id"]
        assert payload.credits == 30
        return {
            "checkout_url": "https://billing.local/checkout/intent_123",
            "provider_intent_id": "intent_123",
        }

    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setattr(BillingService, "create_purchase_intent", staticmethod(fake_create_purchase_intent))

    intent = client.post(
        "/api/billing/purchase-intent",
        headers=auth_headers(token),
        json={
            "credits": 30,
            "success_url": "https://frontend.local/success",
            "cancel_url": "https://frontend.local/cancel",
        },
    )
    assert intent.status_code == 200
    assert intent.json()["provider_intent_id"] == "intent_123"

    webhook = post_signed_stripe_event(
        client,
        {
            "id": "evt_ms_credit_123",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_ms_credit_123",
                    "mode": "payment",
                    "payment_status": "paid",
                    "metadata": {
                        "purchase_type": "credits",
                        "user_id": str(user["id"]),
                        "credits": "30",
                    },
                }
            },
        },
        "whsec_test",
    )
    assert webhook.status_code == 202

    wallet = client.get("/api/credits/wallet", headers=auth_headers(token))
    assert wallet.status_code == 200
    assert wallet.json()["balance"] == 30
from conftest import confirm_registered_email
