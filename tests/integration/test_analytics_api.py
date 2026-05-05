from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.db.base import Base
from app.db.session import get_db_session
from app.main import create_app


@pytest.fixture
def client(tmp_path: Path, monkeypatch) -> Iterator[TestClient]:
    monkeypatch.setenv("ANALYTICS_REPORT_DIR", str(tmp_path))
    get_settings.cache_clear()
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
        monkeypatch.delenv("ANALYTICS_REPORT_DIR", raising=False)
        get_settings.cache_clear()


def test_analytics_api_summary_breakdowns_and_report(client: TestClient):
    created = client.post("/api/v1/ingestion/text", json={"text": "Payment failed during checkout."}).json()["data"]

    summary = client.get("/api/v1/analytics/summary")
    trends = client.get("/api/v1/analytics/feedback-trends")
    sentiment = client.get("/api/v1/analytics/sentiment-breakdown")
    tickets = client.get("/api/v1/analytics/tickets")
    reviews = client.get("/api/v1/analytics/reviews")
    evaluations = client.get("/api/v1/analytics/evaluations")
    executive = client.get("/api/v1/analytics/executive-summary")
    report = client.get("/api/v1/analytics/report")

    assert created["feedback_id"] is not None
    assert summary.status_code == 200
    assert summary.json()["data"]["total_feedback"] == 1
    assert trends.status_code == 200
    assert sentiment.status_code == 200
    assert tickets.status_code == 200
    assert reviews.status_code == 200
    assert evaluations.status_code == 200
    assert executive.status_code == 200
    assert report.status_code == 200
    assert Path(report.json()["data"]["report_path"]).exists()


def test_analytics_api_requires_permission_when_auth_enabled(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEYS", "analyst-key:analyst,reviewer-key:reviewer")
    monkeypatch.setenv("ANALYTICS_REPORT_DIR", str(tmp_path))
    get_settings.cache_clear()
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
        test_client = TestClient(app)
        missing = test_client.get("/api/v1/analytics/summary")
        allowed = test_client.get("/api/v1/analytics/summary", headers={"X-API-Key": "analyst-key"})
        denied = test_client.get("/api/v1/analytics/summary", headers={"X-API-Key": "reviewer-key"})
    finally:
        app.dependency_overrides.clear()
        monkeypatch.delenv("AUTH_ENABLED", raising=False)
        monkeypatch.delenv("API_KEYS", raising=False)
        monkeypatch.delenv("ANALYTICS_REPORT_DIR", raising=False)
        get_settings.cache_clear()

    assert missing.status_code == 401
    assert allowed.status_code == 200
    assert denied.status_code == 403
