from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.db.base import Base
from app.domain.analysis.repository import AnalysisRepository
from app.domain.analysis.service import AnalysisService
from app.domain.feedback.models import FeedbackProcessingStatus, FeedbackSourceType
from app.domain.feedback.repository import FeedbackRepository
from app.domain.feedback.service import FeedbackService
from app.domain.llm.fake_provider import FakeLLMProvider
from app.domain.retrieval.retrieval_service import RetrievalSearchResult
from app.domain.retrieval.vector_store import SearchResult


class FakeRetrievalService:
    def search_with_options(self, query: str, *, top_k: int, filters=None, persist_trace=False, feedback_record_id=None):
        return RetrievalSearchResult(
            results=[SearchResult(text="Payment runbook context", score=0.9, rank=1, chunk_id=11)],
            rag_context="Payment runbook context",
            trace_id=22 if persist_trace else None,
        )


def _session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def test_analysis_service_persists_run_and_updates_feedback():
    session_factory = _session_factory()
    with session_factory() as session:
        feedback_service = FeedbackService(FeedbackRepository(session))
        record = feedback_service.create_ingested_feedback(
            source_type=FeedbackSourceType.TEXT,
            raw_text="Payment failed.",
            extracted_text="Payment failed.",
            processing_status=FeedbackProcessingStatus.EXTRACTED,
        )
        service = AnalysisService(
            repository=AnalysisRepository(session),
            feedback_service=feedback_service,
            retrieval_service=FakeRetrievalService(),
            provider=FakeLLMProvider(),
            fallback_provider=None,
            settings=Settings(),
        )

        response = service.run_feedback_analysis(record.id)

        updated = feedback_service.get_feedback_record(record.id)
        assert response.analysis_run_id == updated.latest_analysis_run_id
        assert response.retrieval_trace_id == 22
        assert updated.category == "PAYMENT"
        assert updated.processing_status == FeedbackProcessingStatus.COMPLETED
