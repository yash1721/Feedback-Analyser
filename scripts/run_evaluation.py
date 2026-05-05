import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import get_settings
from app.db.session import get_session_factory
from app.dependencies import build_retrieval_service
from app.domain.evaluation.datasets import EvaluationDatasetLoader
from app.domain.evaluation.repository import EvaluationRepository
from app.domain.evaluation.report import EvaluationReportGenerator
from app.domain.evaluation.schemas import EvaluationRunCreate
from app.domain.evaluation.service import EvaluationService
from app.domain.llm.fake_provider import FakeLLMProvider
from app.domain.llm.rule_based_provider import RuleBasedAnalysisProvider
from app.domain.retrieval.retrieval_service import RetrievalSearchResult
from app.domain.retrieval.vector_store import SearchResult


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a FeedbackIQ evaluation benchmark.")
    parser.add_argument("--dataset", "--dataset-path", dest="dataset_path", default=None)
    parser.add_argument("--dataset-name", default=None)
    parser.add_argument("--provider", choices=["fake", "rule_based"], default=None)
    parser.add_argument("--model-name", default=None)
    parser.add_argument("--prompt-version", default=None)
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--no-report", action="store_true")
    parser.add_argument("--live-retrieval", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    provider = _provider(args.provider, args.model_name)
    session_factory = get_session_factory()
    with session_factory() as session:
        service = EvaluationService(
            repository=EvaluationRepository(session),
            retrieval_service=build_retrieval_service() if args.live_retrieval else FixtureRetrievalService(),
            provider=provider,
            settings=settings,
            dataset_loader=EvaluationDatasetLoader(),
            report_generator=EvaluationReportGenerator(settings.evaluation_report_dir),
        )
        result = service.run_evaluation(
            EvaluationRunCreate(
                dataset_path=args.dataset_path,
                dataset_name=args.dataset_name,
                provider=args.provider,
                model_name=args.model_name,
                prompt_version=args.prompt_version,
                top_k=args.top_k,
                write_report=not args.no_report,
            )
        )
        print(json.dumps(result.model_dump(mode="json"), indent=2))


def _provider(provider_name: str | None, model_name: str | None):
    if provider_name == "fake":
        return FakeLLMProvider(model_name or "fake-feedback-analyzer")
    return RuleBasedAnalysisProvider(model_name or "rule-based-feedback-analyzer-v1")


class FixtureRetrievalService:
    def search_with_options(self, query: str, *, top_k: int, filters=None, persist_trace=False, feedback_record_id=None):
        query_lower = query.lower()
        results = []
        for index, item in enumerate(_fixture_results(query_lower), start=1):
            results.append(
                SearchResult(
                    text=item["text"],
                    score=1.0 - (index - 1) * 0.05,
                    rank=index,
                    chunk_id=index,
                    metadata={"document_title": item["document_title"]},
                )
            )
        return RetrievalSearchResult(results=results[:top_k], rag_context="\n".join(result.text for result in results[:top_k]), trace_id=None)


def _fixture_results(query: str) -> list[dict]:
    if any(word in query for word in ["payment", "checkout", "refund"]):
        return [
            {
                "document_title": "Payments Knowledge Base",
                "text": "Payment failures during checkout and refund delays should route to the Payment Team.",
            }
        ]
    if any(word in query for word in ["shipment", "delivery", "tracking"]):
        return [
            {
                "document_title": "Delivery Knowledge Base",
                "text": "Shipment delays, delivery tracking problems, and logistics issues should route to the Logistics Team.",
            }
        ]
    if any(word in query for word in ["button", "mobile", "screen", "ui"]):
        return [
            {
                "document_title": "Frontend Experience Guide",
                "text": "Mobile screen, checkout button, design, and UI confusion should route to the Frontend Team.",
            }
        ]
    if any(word in query for word in ["fraud", "security", "breach"]):
        return [
            {
                "document_title": "Security Incident Runbook",
                "text": "Fraud, security breach, and account risk reports should route to the Backend Team immediately.",
            }
        ]
    return [
        {
            "document_title": "Customer Support Guide",
            "text": "General feedback without a clear owner should route to the Customer Support Team.",
        }
    ]


if __name__ == "__main__":
    main()
