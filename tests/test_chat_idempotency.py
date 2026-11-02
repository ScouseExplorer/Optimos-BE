from sqlalchemy.orm import Session

from app.models.chat import Chat
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
    admin_user, admin_token = register_and_login(client, "chatadmin@example.com", "chat_admin_user")
    promote_to_admin(db_session_factory, admin_user["id"])

    response = client.post(
        "/api/credits/admin/adjust",
        headers=auth_headers(admin_token),
        json={"user_id": user_id, "amount": amount, "description": "idempotency test top-up"},
    )
    assert response.status_code == 201


def test_chat_generation_idempotency_key_reuse_returns_same_chat(client, db_session_factory):
    user, token = register_and_login(client, "chat@example.com", "chat_user")
    top_up_user_credits(client, db_session_factory, user["id"], amount=20)

    headers = auth_headers(token)
    headers["Idempotency-Key"] = "idem-123"

    payload = {"user_message": "Give me one post idea about software engineering careers"}

    first = client.post("/api/chats", headers=headers, json=payload)
    second = client.post("/api/chats", headers=headers, json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]

    db: Session = db_session_factory()
    try:
        total = db.query(Chat).filter(Chat.user_id == user["id"]).count()
        assert total == 1
    finally:
        db.close()
from conftest import confirm_registered_email
