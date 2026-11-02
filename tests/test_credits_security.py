from sqlalchemy.orm import Session

from app.models.user import User


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register_and_login(client, email: str, username: str, password: str = "Pass12345!"):
    response = client.post(
        "/api/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    assert response.status_code == 201
    confirm_registered_email(client, email)
    user = response.json()

    login = client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return user, token


def test_wallet_is_user_scoped(client):
    _, token_a = register_and_login(client, "walleta@example.com", "wallet_a")
    _, token_b = register_and_login(client, "walletb@example.com", "wallet_b")

    wallet_a = client.get("/api/credits/wallet", headers=auth_headers(token_a))
    wallet_b = client.get("/api/credits/wallet", headers=auth_headers(token_b))

    assert wallet_a.status_code == 200
    assert wallet_b.status_code == 200
    assert wallet_a.json()["user_id"] != wallet_b.json()["user_id"]


def test_non_admin_cannot_adjust_credits(client):
    user, token = register_and_login(client, "normal@example.com", "normal_user")

    response = client.post(
        "/api/credits/admin/adjust",
        headers=auth_headers(token),
        json={"user_id": user["id"], "amount": 10, "description": "nope"},
    )

    assert response.status_code == 403


def test_admin_can_adjust_credits(client, db_session_factory):
    target_user, _ = register_and_login(client, "target@example.com", "target_user")
    admin_user, admin_token = register_and_login(client, "admin@example.com", "admin_user")

    db: Session = db_session_factory()
    try:
        admin_row = db.query(User).filter(User.id == admin_user["id"]).first()
        admin_row.is_admin = True
        db.commit()
    finally:
        db.close()

    adjust = client.post(
        "/api/credits/admin/adjust",
        headers=auth_headers(admin_token),
        json={"user_id": target_user["id"], "amount": 25, "description": "grant"},
    )
    assert adjust.status_code == 201

    target_login = client.post(
        "/api/auth/login",
        data={"username": "target_user", "password": "Pass12345!"},
    )
    target_token = target_login.json()["access_token"]

    wallet = client.get("/api/credits/wallet", headers=auth_headers(target_token))
    assert wallet.status_code == 200
    assert wallet.json()["balance"] == 25
from conftest import confirm_registered_email
