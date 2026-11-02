from sqlalchemy.orm import Session

from app.models.ai_usage import AIUsage
from app.models.chat import Chat
from app.models.subscription import Subscription


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


def test_experience_crud_is_user_scoped(client):
    user_a, token_a = register_and_login(client, "expa@example.com", "exp_user_a")
    _, token_b = register_and_login(client, "expb@example.com", "exp_user_b")

    created = client.post(
        "/api/experiences",
        headers=auth_headers(token_a),
        json={
            "title": "Shipped a migration",
            "description": "Migrated a service safely.",
            "category": "engineering",
            "importance": 4,
        },
    )
    assert created.status_code == 201
    experience_id = created.json()["id"]

    forbidden_update = client.patch(
        f"/api/experiences/{experience_id}",
        headers=auth_headers(token_b),
        json={"title": "hijack"},
    )
    assert forbidden_update.status_code == 404

    forbidden_delete = client.delete(
        f"/api/experiences/{experience_id}",
        headers=auth_headers(token_b),
    )
    assert forbidden_delete.status_code == 404

    list_a = client.get("/api/experiences", headers=auth_headers(token_a))
    list_b = client.get("/api/experiences", headers=auth_headers(token_b))
    assert list_a.status_code == 200
    assert list_b.status_code == 200
    assert list_a.json()["total"] == 1
    assert list_a.json()["items"][0]["user_id"] == user_a["id"]
    assert list_b.json()["total"] == 0


def test_opinion_and_post_crud_is_user_scoped(client):
    user_a, token_a = register_and_login(client, "oppa@example.com", "opp_user_a")
    _, token_b = register_and_login(client, "oppb@example.com", "opp_user_b")

    opinion = client.post(
        "/api/opinions",
        headers=auth_headers(token_a),
        json={"topic": "remote work", "opinion": "Hybrid is strongest", "confidence": 4},
    )
    assert opinion.status_code == 201
    opinion_id = opinion.json()["id"]

    post = client.post(
        "/api/posts",
        headers=auth_headers(token_a),
        json={"content": "A tactical LinkedIn post", "topic": "career"},
    )
    assert post.status_code == 201
    post_id = post.json()["id"]

    cross_update_opinion = client.patch(
        f"/api/opinions/{opinion_id}",
        headers=auth_headers(token_b),
        json={"opinion": "tampered"},
    )
    assert cross_update_opinion.status_code == 404

    cross_delete_post = client.delete(
        f"/api/posts/{post_id}",
        headers=auth_headers(token_b),
    )
    assert cross_delete_post.status_code == 404

    opinions_a = client.get("/api/opinions", headers=auth_headers(token_a))
    opinions_b = client.get("/api/opinions", headers=auth_headers(token_b))
    posts_a = client.get("/api/posts", headers=auth_headers(token_a))
    posts_b = client.get("/api/posts", headers=auth_headers(token_b))

    assert opinions_a.status_code == 200
    assert opinions_b.status_code == 200
    assert posts_a.status_code == 200
    assert posts_b.status_code == 200

    assert opinions_a.json()["total"] == 1
    assert opinions_a.json()["items"][0]["user_id"] == user_a["id"]
    assert opinions_b.json()["total"] == 0

    assert posts_a.json()["total"] == 1
    assert posts_a.json()["items"][0]["user_id"] == user_a["id"]
    assert posts_b.json()["total"] == 0


def test_chat_delete_is_user_scoped(client, db_session_factory):
    user_a, token_a = register_and_login(client, "chata@example.com", "chat_user_a")
    _, token_b = register_and_login(client, "chatb@example.com", "chat_user_b")

    db: Session = db_session_factory()
    try:
        subscription = db.query(Subscription).filter(Subscription.user_id == user_a["id"]).first()
        chat = Chat(
            user_id=user_a["id"],
            subscription_id=subscription.id,
            user_message="hello",
            ai_response="world",
            tokens_used=1,
            request_id="manual-seed-chat",
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)
        chat_id = chat.id
    finally:
        db.close()

    forbidden_delete = client.delete(f"/api/chats/{chat_id}", headers=auth_headers(token_b))
    assert forbidden_delete.status_code == 404

    own_list = client.get("/api/chats", headers=auth_headers(token_a))
    assert own_list.status_code == 200
    assert own_list.json()["total"] == 1
    assert own_list.json()["chats"][0]["id"] == chat_id


def test_profile_and_subscription_views_are_isolated(client):
    _, token_a = register_and_login(client, "profa@example.com", "prof_user_a")
    _, token_b = register_and_login(client, "profb@example.com", "prof_user_b")

    update_a = client.patch(
        "/api/users/me/profile",
        headers=auth_headers(token_a),
        json={"display_name": "Tenant A"},
    )
    assert update_a.status_code == 200

    profile_a = client.get("/api/users/me/profile", headers=auth_headers(token_a))
    profile_b = client.get("/api/users/me/profile", headers=auth_headers(token_b))
    assert profile_a.status_code == 200
    assert profile_b.status_code == 200
    assert profile_a.json()["display_name"] == "Tenant A"
    assert profile_b.json()["display_name"] != "Tenant A"

    upgrade_a = client.post("/api/subscriptions/upgrade/pro", headers=auth_headers(token_a))
    assert upgrade_a.status_code == 200

    sub_a = client.get("/api/subscriptions/me", headers=auth_headers(token_a))
    sub_b = client.get("/api/subscriptions/me", headers=auth_headers(token_b))
    assert sub_a.status_code == 200
    assert sub_b.status_code == 200
    assert sub_a.json()["tier"] == "pro"
    assert sub_b.json()["tier"] == "free"


def test_usage_endpoint_returns_only_current_user_entries(client, db_session_factory):
    user_a, token_a = register_and_login(client, "usa@example.com", "usage_user_a")
    user_b, token_b = register_and_login(client, "usb@example.com", "usage_user_b")

    db: Session = db_session_factory()
    try:
        db.add(
            AIUsage(
                user_id=user_a["id"],
                action="generate_post",
                model="test-model",
                status="success",
                credits_charged=0,
                input_tokens=11,
                output_tokens=22,
                estimated_cost=0.01,
                request_id="usage-a-1",
            )
        )
        db.add(
            AIUsage(
                user_id=user_b["id"],
                action="generate_post",
                model="test-model",
                status="success",
                credits_charged=0,
                input_tokens=33,
                output_tokens=44,
                estimated_cost=0.02,
                request_id="usage-b-1",
            )
        )
        db.commit()
    finally:
        db.close()

    usage_a = client.get("/api/usage/me", headers=auth_headers(token_a))
    usage_b = client.get("/api/usage/me", headers=auth_headers(token_b))
    assert usage_a.status_code == 200
    assert usage_b.status_code == 200
    assert usage_a.json()["total"] == 1
    assert usage_b.json()["total"] == 1
    assert usage_a.json()["items"][0]["user_id"] == user_a["id"]
    assert usage_b.json()["items"][0]["user_id"] == user_b["id"]
from conftest import confirm_registered_email
