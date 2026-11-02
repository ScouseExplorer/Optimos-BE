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


def test_e2e_auth_to_ai_usage_wallet_and_post_save_flow(client, db_session_factory):
    # 1) Auth + user setup
    user, user_token = register_and_login(client, "journey@example.com", "journey_user")
    admin, admin_token = register_and_login(client, "journeyadmin@example.com", "journey_admin")
    promote_to_admin(db_session_factory, admin["id"])

    # 2) Simulate user profile setup in frontend
    profile_update = client.patch(
        "/api/users/me/profile",
        headers=auth_headers(user_token),
        json={
            "display_name": "Akin",
            "bio": "I help founders convert product stories into customer trust.",
        },
    )
    assert profile_update.status_code == 200

    # 3) Seed an existing post so the user has historical content in their account
    existing_post = client.post(
        "/api/posts",
        headers=auth_headers(user_token),
        json={
            "content": "Previous post about product discovery experiments.",
            "topic": "product",
            "post_format": "text",
        },
    )
    assert existing_post.status_code == 201

    # 4) Simulate buying credits with current backend capability (admin adjustment)
    top_up = client.post(
        "/api/credits/admin/adjust",
        headers=auth_headers(admin_token),
        json={"user_id": user["id"], "amount": 50, "description": "purchase top-up simulation"},
    )
    assert top_up.status_code == 201

    wallet_before = client.get("/api/credits/wallet", headers=auth_headers(user_token))
    assert wallet_before.status_code == 200
    assert wallet_before.json()["balance"] == 50

    # 5) Make generation consume credits to validate end-to-end accounting
    set_feature_cost(db_session_factory, "generate_post", 10)

    # 6) AI generation call (ML-thinking placeholder path currently)
    chat_headers = auth_headers(user_token)
    chat_headers["Idempotency-Key"] = "journey-e2e-001"
    chat = client.post(
        "/api/chats",
        headers=chat_headers,
        json={"user_message": "Analyze my posting style and draft one stronger post idea."},
    )
    assert chat.status_code == 200
    chat_body = chat.json()
    assert chat_body["tokens_used"] > 0
    assert "personalized post idea" in chat_body["ai_response"].lower()

    # 7) Usage and subscription counters should reflect the generation
    usage = client.get("/api/usage/me", headers=auth_headers(user_token))
    assert usage.status_code == 200
    assert usage.json()["total"] >= 1
    latest_usage = usage.json()["items"][0]
    assert latest_usage["status"] == "success"
    assert latest_usage["input_tokens"] is not None
    assert latest_usage["output_tokens"] is not None

    subscription_usage = client.get("/api/subscriptions/usage", headers=auth_headers(user_token))
    assert subscription_usage.status_code == 200
    assert subscription_usage.json()["messages_used"] == 1

    # 8) Wallet/ledger should reflect credit deduction for generation
    wallet_after = client.get("/api/credits/wallet", headers=auth_headers(user_token))
    assert wallet_after.status_code == 200
    assert wallet_after.json()["balance"] == 40

    tx = client.get("/api/credits/transactions", headers=auth_headers(user_token))
    assert tx.status_code == 200
    assert tx.json()["total"] >= 2
    amounts = [row["amount"] for row in tx.json()["items"]]
    types = [row["transaction_type"] for row in tx.json()["items"]]
    assert 50 in amounts
    assert -10 in amounts
    assert "ADMIN_ADJUSTMENT" in types
    assert "RESERVATION" in types

    # 9) Save the generated output as a user post
    save_generated = client.post(
        "/api/posts",
        headers=auth_headers(user_token),
        json={
            "content": chat_body["ai_response"],
            "topic": "analysis-derived",
            "post_format": "text",
        },
    )
    assert save_generated.status_code == 201

    all_posts = client.get("/api/posts", headers=auth_headers(user_token))
    assert all_posts.status_code == 200
    assert all_posts.json()["total"] == 2
from conftest import confirm_registered_email
