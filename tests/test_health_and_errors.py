def test_liveness_endpoint(client):
    response = client.get("/health/live")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "alive"


def test_readiness_endpoint(client):
    response = client.get("/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert "checks" in body
    assert body["checks"]["database"] is True


def test_structured_error_envelope_for_unauthorized(client):
    response = client.get("/api/users/me")

    assert response.status_code == 401
    body = response.json()
    assert "error" in body
    assert body["error"]["status"] == 401
    assert body["error"]["code"] == "HTTP_401"
    assert "request_id" in body["error"]
    assert "detail" in body
