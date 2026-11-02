from typing import Any

from sqlalchemy.orm import Session

from app.models.user import User


def auth_headers(token: str) -> dict[str, str]:
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


def request(client, method: str, path: str, headers: dict[str, str] | None = None, json: dict[str, Any] | None = None):
    if method == "GET":
        return client.get(path, headers=headers)
    if method == "POST":
        return client.post(path, headers=headers, json=json)
    if method == "PATCH":
        return client.patch(path, headers=headers, json=json)
    if method == "DELETE":
        return client.delete(path, headers=headers)
    raise ValueError(f"Unsupported method: {method}")


def test_public_routes_access_without_auth(client):
    # readiness may return 503 if deps are unavailable in some environments.
    routes = [
        ("GET", "/", None, {200}),
        ("GET", "/health", None, {200}),
        ("GET", "/health/live", None, {200}),
        ("GET", "/health/ready", None, {200, 503}),
        (
            "POST",
            "/api/auth/register",
            {"email": "publicreg@example.com", "username": "public_reg", "password": "Pass12345!"},
            {201},
        ),
    ]

    for method, path, payload, expected in routes:
        response = request(client, method, path, json=payload)
        assert response.status_code in expected


def test_auth_required_matrix_for_protected_routes(client):
    protected = [
        ("GET", "/api/users/me", None),
        ("GET", "/api/users/1", None),
        ("GET", "/api/users/me/profile", None),
        ("PATCH", "/api/users/me/profile", {"display_name": "NoAuth"}),
        ("GET", "/api/users/me/notifications", None),
        ("PATCH", "/api/users/me/notifications", {"email_billing": False}),
        ("GET", "/api/users/me/security", None),
        ("PATCH", "/api/users/me/security", {"session_timeout_minutes": 45}),
        ("GET", "/api/chats", None),
        ("POST", "/api/chats", {"user_message": "hello"}),
        ("DELETE", "/api/chats", None),
        ("GET", "/api/subscriptions/me", None),
        ("POST", "/api/subscriptions/upgrade/pro", None),
        ("GET", "/api/subscriptions/usage", None),
        ("GET", "/api/subscriptions/entitlements", None),
        ("GET", "/api/credits/wallet", None),
        ("GET", "/api/credits/transactions", None),
        ("GET", "/api/credits/feature-costs", None),
        ("POST", "/api/credits/admin/adjust", {"user_id": 1, "amount": 1, "description": "test"}),
        ("GET", "/api/usage/me", None),
        ("GET", "/api/experiences", None),
        ("POST", "/api/experiences", {"title": "x", "description": "y", "importance": 3}),
        ("GET", "/api/opinions", None),
        ("POST", "/api/opinions", {"topic": "x", "opinion": "y", "confidence": 3}),
        ("GET", "/api/posts", None),
        ("POST", "/api/posts", {"content": "hello"}),
        ("GET", "/api/global-datasets", None),
        ("GET", "/api/global-datasets/1", None),
        ("POST", "/api/global-datasets", {"dataset_key": "hooks", "item_key": "x", "title": "t", "content": "c"}),
        ("GET", "/api/global-datasets/admin/all", None),
        ("GET", "/api/admin/stats", None),
        ("GET", "/api/admin/users", None),
        ("GET", "/api/admin/chat-stats", None),
        ("POST", "/api/auth/logout", {}),
    ]

    for method, path, payload in protected:
        response = request(client, method, path, json=payload)
        assert response.status_code == 401


def test_admin_only_routes_reject_non_admin_and_allow_admin(client, db_session_factory):
    target_user, _ = register_and_login(client, "targetpol@example.com", "target_policy")
    _, user_token = register_and_login(client, "userpol@example.com", "user_policy")
    admin_user, admin_token = register_and_login(client, "adminpol@example.com", "admin_policy")
    promote_to_admin(db_session_factory, admin_user["id"])

    # Seed one global item for update/delete checks.
    create_global = client.post(
        "/api/global-datasets",
        headers=auth_headers(admin_token),
        json={
            "dataset_key": "policy",
            "item_key": "matrix_01",
            "title": "policy title",
            "content": "policy content",
        },
    )
    assert create_global.status_code == 201
    item_id = create_global.json()["id"]

    cases = [
        ("GET", "/api/admin/stats", None, {200}),
        ("GET", "/api/admin/users", None, {200}),
        ("GET", "/api/admin/chat-stats", None, {200}),
        (
            "POST",
            "/api/credits/admin/adjust",
            {"user_id": target_user["id"], "amount": 5, "description": "matrix"},
            {201},
        ),
        ("GET", "/api/global-datasets/admin/all", None, {200}),
        (
            "PATCH",
            f"/api/global-datasets/{item_id}",
            {"title": "updated title"},
            {200},
        ),
        ("DELETE", f"/api/global-datasets/{item_id}", None, {204}),
    ]

    for method, path, payload, admin_expected in cases:
        non_admin = request(client, method, path, headers=auth_headers(user_token), json=payload)
        assert non_admin.status_code == 403

        admin = request(client, method, path, headers=auth_headers(admin_token), json=payload)
        assert admin.status_code in admin_expected
from conftest import confirm_registered_email
