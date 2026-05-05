from collections.abc import Iterator
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db.base import Base
from app.db.session import get_db_session
from app.dependencies import get_evaluation_service
from app.domain.evaluation.repository import EvaluationRepository
from app.domain.evaluation.report import EvaluationReportGenerator
from app.domain.evaluation.service import EvaluationService
from app.domain.llm.fake_provider import FakeLLMProvider
from app.domain.retrieval.retrieval_service import RetrievalSearchResult
from app.domain.retrieval.vector_store import SearchResult
from app.main import create_app


class FakeRetrievalService:
    def search_with_options(self, query: str, *, top_k: int, filters=None, persist_trace=False, feedback_record_id=None):
        return RetrievalSearchResult(
            results=[SearchResult(text="Payment checkout evidence", score=0.9, rank=1, chunk_id=5)],
            rag_context="Payment checkout evidence",
            trace_id=None,
        )


@pytest.fixture
def client() -> Iterator[TestClient]:
    report_dir = Path(".test_eval_api")
    shutil.rmtree(report_dir, ignore_errors=True)
    report_dir.mkdir(parents=True, exist_ok=True)
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

    def override_evaluation_service() -> Iterator[EvaluationService]:
        with session_factory() as session:
            yield EvaluationService(
                repository=EvaluationRepository(session),
                retrieval_service=FakeRetrievalService(),
                provider=FakeLLMProvider(),
                settings=Settings(evaluation_report_dir=str(report_dir)),
                report_generator=EvaluationReportGenerator(report_dir),
            )

    app = create_app()
    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_evaluation_service] = override_evaluation_service
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        shutil.rmtree(report_dir, ignore_errors=True)


def test_evaluation_run_list_get_and_report_api(client: TestClient):
    created = client.post("/api/v1/evaluations/runs", json={"provider": "fake", "write_report": True})

    assert created.status_code == 200
    run_id = created.json()["data"]["run"]["id"]

    listed = client.get("/api/v1/evaluations/runs")
    detail = client.get(f"/api/v1/evaluations/runs/{run_id}")
    report = client.get(f"/api/v1/evaluations/runs/{run_id}/report")

    assert listed.status_code == 200
    assert listed.json()["data"]["total"] == 1
    assert detail.status_code == 200
    assert len(detail.json()["data"]["items"]) == 4
    assert report.status_code == 200
    assert "FeedbackIQ Evaluation Run" in report.text
