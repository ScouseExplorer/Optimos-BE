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

    login = client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
    )
    assert login.status_code == 200
    return response.json(), login.json()["access_token"]


def promote_to_admin(db_session_factory, user_id: int) -> None:
    db: Session = db_session_factory()
    try:
        row = db.query(User).filter(User.id == user_id).first()
        row.is_admin = True
        db.commit()
    finally:
        db.close()


def test_global_dataset_read_requires_auth(client):
    response = client.get("/api/global-datasets")
    assert response.status_code == 401


def test_non_admin_cannot_create_global_dataset_item(client):
    _, user_token = register_and_login(client, "reader@example.com", "reader_user")

    response = client.post(
        "/api/global-datasets",
        headers=auth_headers(user_token),
        json={
            "dataset_key": "hooks",
            "item_key": "hook_01",
            "title": "Open with a contrarian claim",
            "content": "Start with a respectful contradiction to common advice.",
            "tags": ["hook", "contrarian"],
            "priority": 2,
            "is_active": True,
        },
    )

    assert response.status_code == 403


def test_admin_can_create_and_user_can_read_active_global_item(client, db_session_factory):
    _, user_token = register_and_login(client, "reader2@example.com", "reader_user2")
    admin, admin_token = register_and_login(client, "admin2@example.com", "admin_user2")
    promote_to_admin(db_session_factory, admin["id"])

    create = client.post(
        "/api/global-datasets",
        headers=auth_headers(admin_token),
        json={
            "dataset_key": "hooks",
            "item_key": "hook_02",
            "title": "Lead with a specific metric",
            "content": "Mention a concrete before/after KPI in the first sentence.",
            "tags": ["hook", "metrics"],
            "source": "content-team-playbook-v1",
            "priority": 5,
            "is_active": True,
        },
    )
    assert create.status_code == 201
    item_id = create.json()["id"]

    listing = client.get(
        "/api/global-datasets?dataset_key=hooks",
        headers=auth_headers(user_token),
    )
    assert listing.status_code == 200
    body = listing.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == item_id
    assert body["items"][0]["dataset_key"] == "hooks"
    assert body["items"][0]["item_key"] == "hook_02"

    detail = client.get(f"/api/global-datasets/{item_id}", headers=auth_headers(user_token))
    assert detail.status_code == 200
    assert detail.json()["title"] == "Lead with a specific metric"


def test_inactive_global_item_hidden_from_user_reads_but_visible_to_admin(client, db_session_factory):
    _, user_token = register_and_login(client, "reader3@example.com", "reader_user3")
    admin, admin_token = register_and_login(client, "admin3@example.com", "admin_user3")
    promote_to_admin(db_session_factory, admin["id"])

    create = client.post(
        "/api/global-datasets",
        headers=auth_headers(admin_token),
        json={
            "dataset_key": "angles",
            "item_key": "angle_01",
            "title": "Explain trade-offs",
            "content": "Frame decisions as explicit trade-offs to build trust.",
            "tags": ["angles"],
            "priority": 1,
            "is_active": False,
        },
    )
    assert create.status_code == 201
    item_id = create.json()["id"]

    listing = client.get(
        "/api/global-datasets?dataset_key=angles",
        headers=auth_headers(user_token),
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 0

    detail = client.get(f"/api/global-datasets/{item_id}", headers=auth_headers(user_token))
    assert detail.status_code == 404

    admin_listing = client.get(
        "/api/global-datasets/admin/all?dataset_key=angles&include_inactive=true",
        headers=auth_headers(admin_token),
    )
    assert admin_listing.status_code == 200
    assert admin_listing.json()["total"] == 1
    assert admin_listing.json()["items"][0]["is_active"] is False
from conftest import confirm_registered_email
