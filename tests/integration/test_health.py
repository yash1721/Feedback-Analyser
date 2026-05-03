from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint_returns_standard_response():
    client = TestClient(create_app())

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
    assert body["error"] is None

