import json
import shutil
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db.base import Base
from app.domain.evaluation.repository import EvaluationRepository
from app.domain.evaluation.report import EvaluationReportGenerator
from app.domain.evaluation.schemas import EvaluationRunCreate
from app.domain.evaluation.service import EvaluationService
from app.domain.llm.fake_provider import FakeLLMProvider
from app.domain.retrieval.retrieval_service import RetrievalSearchResult
from app.domain.retrieval.vector_store import SearchResult


class FakeRetrievalService:
    def search_with_options(self, query: str, *, top_k: int, filters=None, persist_trace=False, feedback_record_id=None):
        return RetrievalSearchResult(
            results=[
                SearchResult(
                    text="Payment checkout evidence",
                    score=0.9,
                    rank=1,
                    chunk_id=5,
                    metadata={"document_title": "Payments Knowledge Base"},
                )
            ],
            rag_context="Payment checkout evidence",
            trace_id=None,
        )


def _session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _dataset(base_dir: Path):
    path = base_dir / "dataset.json"
    path.write_text(
        json.dumps(
            {
                "name": "unit_seed",
                "version": "v1",
                "examples": [
                    {
                        "id": "payment_001",
                        "feedback_text": "Payment failed during checkout.",
                        "expected_sentiment": "NEGATIVE",
                        "expected_category": "PAYMENT",
                        "expected_severity": "P2",
                        "expected_routed_team": "Payment Team",
                        "expected_keywords": ["payment", "checkout"],
                        "expected_relevant_chunk_ids": [5],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_evaluation_service_persists_run_items_and_report():
    report_dir = Path(".test_eval_service")
    shutil.rmtree(report_dir, ignore_errors=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    session_factory = _session_factory()
    try:
        with session_factory() as session:
            service = EvaluationService(
                repository=EvaluationRepository(session),
                retrieval_service=FakeRetrievalService(),
                provider=FakeLLMProvider(),
                settings=Settings(evaluation_report_dir=str(report_dir)),
                report_generator=EvaluationReportGenerator(report_dir),
            )

            result = service.run_evaluation(EvaluationRunCreate(dataset_path=str(_dataset(report_dir))))
            run = service.get_run(result.run.id)

            assert result.metrics["analysis"]["exact_label_match_rate"] == 1.0
            assert len(run.items) == 1
            assert run.report_path is not None
            assert run.items[0].predicted_json["category"] == "PAYMENT"
    finally:
        shutil.rmtree(report_dir, ignore_errors=True)
