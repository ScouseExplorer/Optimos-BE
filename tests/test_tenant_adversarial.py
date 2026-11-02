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


def test_rapid_cross_tenant_experience_mutation_attempts_are_rejected(client):
    _, token_a = register_and_login(client, "rapidexpa@example.com", "rapid_exp_a")
    _, token_b = register_and_login(client, "rapidexpb@example.com", "rapid_exp_b")

    owner_ids = []
    for i in range(12):
        created = client.post(
            "/api/experiences",
            headers=auth_headers(token_a),
            json={
                "title": f"owner-title-{i}",
                "description": "owner description",
                "category": "engineering",
                "importance": 3,
            },
        )
        assert created.status_code == 201
        owner_ids.append(created.json()["id"])

    # Adversarial loop: repeated update/delete attempts on another tenant's records.
    for record_id in owner_ids:
        for attempt in range(5):
            update = client.patch(
                f"/api/experiences/{record_id}",
                headers=auth_headers(token_b),
                json={"title": f"hijack-{attempt}"},
            )
            assert update.status_code == 404

        delete = client.delete(
            f"/api/experiences/{record_id}",
            headers=auth_headers(token_b),
        )
        assert delete.status_code == 404

    owner_list = client.get("/api/experiences", headers=auth_headers(token_a))
    attacker_list = client.get("/api/experiences", headers=auth_headers(token_b))
    assert owner_list.status_code == 200
    assert attacker_list.status_code == 200
    assert owner_list.json()["total"] == 12
    assert attacker_list.json()["total"] == 0


def test_rapid_cross_tenant_post_and_opinion_mutation_attempts_are_rejected(client):
    _, token_a = register_and_login(client, "rapidopsa@example.com", "rapid_ops_a")
    _, token_b = register_and_login(client, "rapidopsb@example.com", "rapid_ops_b")

    opinion_ids = []
    post_ids = []

    for i in range(8):
        opinion = client.post(
            "/api/opinions",
            headers=auth_headers(token_a),
            json={"topic": f"topic-{i}", "opinion": "owner opinion", "confidence": 4},
        )
        assert opinion.status_code == 201
        opinion_ids.append(opinion.json()["id"])

        post = client.post(
            "/api/posts",
            headers=auth_headers(token_a),
            json={"content": f"owner post {i}", "topic": "topic"},
        )
        assert post.status_code == 201
        post_ids.append(post.json()["id"])

    for opinion_id in opinion_ids:
        tamper = client.patch(
            f"/api/opinions/{opinion_id}",
            headers=auth_headers(token_b),
            json={"opinion": "malicious overwrite"},
        )
        assert tamper.status_code == 404

    for post_id in post_ids:
        remove = client.delete(
            f"/api/posts/{post_id}",
            headers=auth_headers(token_b),
        )
        assert remove.status_code == 404

    opinions_owner = client.get("/api/opinions", headers=auth_headers(token_a))
    posts_owner = client.get("/api/posts", headers=auth_headers(token_a))
    assert opinions_owner.status_code == 200
    assert posts_owner.status_code == 200
    assert opinions_owner.json()["total"] == 8
    assert posts_owner.json()["total"] == 8


def test_repeated_admin_endpoint_probing_never_allows_non_admin_access(client):
    _, token_user = register_and_login(client, "rapidadminu@example.com", "rapid_admin_user")

    probes = [
        ("GET", "/api/admin/stats"),
        ("GET", "/api/admin/users"),
        ("GET", "/api/admin/chat-stats?days=3"),
        ("GET", "/api/global-datasets/admin/all"),
    ]

    for _ in range(20):
        for method, path in probes:
            if method == "GET":
                response = client.get(path, headers=auth_headers(token_user))
            else:
                raise AssertionError("Unexpected probe method")
            assert response.status_code == 403
from conftest import confirm_registered_email
