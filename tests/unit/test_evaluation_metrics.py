from app.domain.analysis.schemas import StructuredAnalysisOutput
from app.domain.evaluation.metrics import (
    aggregate_item_metrics,
    groundedness_check,
    label_metrics,
    latency_summary,
    retrieval_metrics,
)
from app.domain.evaluation.schemas import EvaluationExampleSchema
from app.domain.retrieval.vector_store import SearchResult


def _example() -> EvaluationExampleSchema:
    return EvaluationExampleSchema(
        id="payment_001",
        feedback_text="Payment failed during checkout.",
        expected_sentiment="NEGATIVE",
        expected_category="PAYMENT",
        expected_severity="P2",
        expected_routed_team="Payment Team",
        expected_keywords=["payment", "checkout"],
        expected_relevant_chunk_ids=[5],
    )


def _output() -> StructuredAnalysisOutput:
    return StructuredAnalysisOutput(
        sentiment_label="NEGATIVE",
        sentiment_score=0.9,
        category="PAYMENT",
        severity="P2",
        routed_team="Payment Team",
        summary="Payment issue.",
        recommended_action="Investigate checkout.",
        confidence_score=0.85,
        reasoning_summary="Evidence supports payment failure.",
        evidence_chunk_ids=[5],
    )


def test_label_metrics_exact_match():
    metrics = label_metrics(_example(), _output())

    assert metrics["sentiment_match"] is True
    assert metrics["exact_label_match"] is True


def test_retrieval_metrics_precision_hit_recall_and_mrr():
    results = [
        SearchResult(text="Payment checkout runbook", score=0.9, rank=1, chunk_id=5),
        SearchResult(text="Delivery runbook", score=0.4, rank=2, chunk_id=9),
    ]

    metrics = retrieval_metrics(_example(), results, top_k=2)

    assert metrics["precision_at_k"] == 0.5
    assert metrics["recall_at_k"] == 1.0
    assert metrics["hit_at_k"] is True
    assert metrics["mrr"] == 1.0


def test_retrieval_recall_is_capped_for_multiple_chunks_from_same_document():
    example = EvaluationExampleSchema(
        id="payment_doc",
        feedback_text="Payment failed.",
        expected_sentiment="NEGATIVE",
        expected_category="PAYMENT",
        expected_severity="P1",
        expected_routed_team="Payment Team",
        expected_relevant_document_titles=["Payments Knowledge Base"],
    )
    results = [
        SearchResult(text="Payment evidence 1", score=0.9, rank=1, chunk_id=1, metadata={"document_title": "Payments Knowledge Base"}),
        SearchResult(text="Payment evidence 2", score=0.8, rank=2, chunk_id=2, metadata={"document_title": "Payments Knowledge Base"}),
        SearchResult(text="Payment evidence 3", score=0.7, rank=3, chunk_id=3, metadata={"document_title": "Payments Knowledge Base"}),
    ]

    metrics = retrieval_metrics(example, results, top_k=3)

    assert metrics["recall_at_k"] == 1.0


def test_groundedness_passes_when_evidence_matches():
    result = groundedness_check(
        _example(),
        _output(),
        [SearchResult(text="Payment checkout runbook", score=0.9, rank=1, chunk_id=5)],
    )

    assert result["status"] == "PASS"


def test_latency_summary_percentiles():
    summary = latency_summary([10, 20, 30, 40])

    assert summary["count"] == 4
    assert summary["p50_ms"] == 25.0
    assert summary["avg_ms"] == 25.0


def test_aggregate_item_metrics():
    metrics = aggregate_item_metrics(
        [
            {
                "sentiment_match": True,
                "category_match": True,
                "severity_match": True,
                "routed_team_match": True,
                "exact_label_match": True,
                "invalid_output": False,
                "low_confidence": False,
                "provider_failed": False,
                "precision_at_k": 1.0,
                "recall_at_k": 1.0,
                "hit_at_k": True,
                "mrr": 1.0,
                "average_retrieval_score": 0.9,
                "no_results": False,
                "groundedness_status": "PASS",
                "total_latency_ms": 12,
            }
        ]
    )

    assert metrics["analysis"]["exact_label_match_rate"] == 1.0
    assert metrics["retrieval"]["hit_at_k"] == 1.0
