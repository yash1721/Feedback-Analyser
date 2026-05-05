from fastapi.testclient import TestClient

from app.main import create_app


def test_correlation_id_header_is_generated_and_returned():
    client = TestClient(create_app())

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]
    assert response.headers["X-Correlation-ID"] == response.headers["X-Request-ID"]


def test_incoming_correlation_id_is_preserved():
    client = TestClient(create_app())

    response = client.get("/api/v1/health", headers={"X-Correlation-ID": "test-correlation-123"})

    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == "test-correlation-123"
    assert response.headers["X-Request-ID"] == "test-correlation-123"


def test_metrics_endpoint_exposes_prometheus_metrics():
    client = TestClient(create_app())
    client.get("/api/v1/health")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "feedbackiq_http_requests_total" in response.text
    assert "feedbackiq_http_request_duration_seconds" in response.text
