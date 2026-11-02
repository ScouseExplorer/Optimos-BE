import re

from conftest import confirm_registered_email, latest_test_email


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register_user(client, email: str, username: str, password: str = "Pass12345!"):
    response = client.post(
        "/api/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    assert response.status_code == 201
    confirm_registered_email(client, email)
    return response.json()


def login_user(client, username_or_email: str, password: str = "Pass12345!"):
    response = client.post(
        "/api/auth/login",
        data={"username": username_or_email, "password": password},
    )
    assert response.status_code == 200
    return response.json()


def test_register_and_login_roundtrip(client):
    register_user(client, "user1@example.com", "user1")
    token_payload = login_user(client, "user1")

    assert "access_token" in token_payload
    assert "refresh_token" in token_payload


def test_registration_requires_single_use_email_verification(client):
    email = "verify@example.com"
    register = client.post(
        "/api/auth/register",
        json={"email": email, "username": "verify_user", "password": "Pass12345!"},
    )
    assert register.status_code == 201
    assert register.json()["is_active"] is False

    before_verification = client.post(
        "/api/auth/login",
        data={"username": "verify_user", "password": "Pass12345!"},
    )
    assert before_verification.status_code == 403

    message = latest_test_email(email, "verify")
    token = re.search(r"[?&]token=([A-Za-z0-9_-]+)", message["text"]).group(1)
    verified = client.post(
        "/api/auth/email-verification/confirm",
        json={"token": token},
    )
    assert verified.status_code == 200
    assert client.post(
        "/api/auth/email-verification/confirm",
        json={"token": token},
    ).status_code == 400
    assert client.post(
        "/api/auth/login",
        data={"username": "verify_user", "password": "Pass12345!"},
    ).status_code == 200


def test_password_reset_is_single_use_and_revokes_existing_sessions(client):
    email = "reset@example.com"
    user = register_user(client, email, "reset_user")
    tokens = login_user(client, "reset_user")

    requested = client.post(
        "/api/auth/password-reset/request",
        json={"email": email},
    )
    assert requested.status_code == 202
    message = latest_test_email(email, "reset")
    token = re.search(r"[?&]token=([A-Za-z0-9_-]+)", message["text"]).group(1)

    reset = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": token, "password": "NewPass12345!"},
    )
    assert reset.status_code == 200
    assert client.post(
        "/api/auth/password-reset/confirm",
        json={"token": token, "password": "AnotherPass123!"},
    ).status_code == 400

    old_access = client.get(
        f"/api/users/{user['id']}",
        headers=auth_headers(tokens["access_token"]),
    )
    assert old_access.status_code == 401
    assert client.post(
        "/api/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    ).status_code == 401
    assert client.post(
        "/api/auth/login",
        data={"username": "reset_user", "password": "Pass12345!"},
    ).status_code == 401
    assert client.post(
        "/api/auth/login",
        data={"username": "reset_user", "password": "NewPass12345!"},
    ).status_code == 200


def test_password_reset_request_does_not_disclose_unknown_email(client):
    response = client.post(
        "/api/auth/password-reset/request",
        json={"email": "not-a-user@example.com"},
    )
    assert response.status_code == 202
    assert "If the account exists" in response.json()["detail"]


def test_user_cannot_fetch_another_user_profile(client):
    user_a = register_user(client, "a@example.com", "user_a")
    user_b = register_user(client, "b@example.com", "user_b")

    token_a = login_user(client, "user_a")["access_token"]

    response = client.get(
        f"/api/users/{user_b['id']}",
        headers=auth_headers(token_a),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Not authorized to access this user"


def test_user_can_fetch_own_profile_by_id(client):
    user_a = register_user(client, "self@example.com", "self_user")
    token_a = login_user(client, "self_user")["access_token"]

    response = client.get(
        f"/api/users/{user_a['id']}",
        headers=auth_headers(token_a),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == user_a["id"]
    assert body["username"] == "self_user"
