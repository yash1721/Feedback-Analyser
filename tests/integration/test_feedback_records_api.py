from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db_session
from app.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_db_session() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_db_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_create_and_get_feedback_record(client: TestClient):
    create_response = client.post("/api/v1/feedback-records", json={"text": "Checkout failed."})

    assert create_response.status_code == 200
    created = create_response.json()["data"]
    assert created["raw_text"] == "Checkout failed."
    assert created["processing_status"] == "PENDING"

    get_response = client.get(f"/api/v1/feedback-records/{created['id']}")

    assert get_response.status_code == 200
    assert get_response.json()["data"]["id"] == created["id"]


def test_list_feedback_records_with_pagination_and_filter(client: TestClient):
    client.post("/api/v1/feedback-records", json={"text": "Payment failed."})
    client.post("/api/v1/feedback-records", json={"text": "Shipping delayed."})

    response = client.get("/api/v1/feedback-records?limit=1&offset=0&processing_status=PENDING")

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["total"] == 2
    assert body["limit"] == 1
    assert len(body["items"]) == 1


def test_update_feedback_record_status(client: TestClient):
    created = client.post("/api/v1/feedback-records", json={"text": "Broken checkout."}).json()["data"]

    response = client.patch(
        f"/api/v1/feedback-records/{created['id']}/status",
        json={
            "processing_status": "FAILED",
            "error_code": "manual_review",
            "error_message": "Needs review.",
        },
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["processing_status"] == "FAILED"
    assert body["error_code"] == "manual_review"


def test_get_missing_feedback_record_returns_404(client: TestClient):
    response = client.get("/api/v1/feedback-records/999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
