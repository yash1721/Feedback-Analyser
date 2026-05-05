from collections.abc import Sequence

from app.domain.analysis.schemas import StructuredAnalysisOutput
from app.domain.evaluation.schemas import EvaluationExampleSchema, GroundednessStatus
from app.domain.retrieval.vector_store import SearchResult


def label_metrics(example: EvaluationExampleSchema, output: StructuredAnalysisOutput | None) -> dict:
    if output is None:
        return {
            "sentiment_match": False,
            "category_match": False,
            "severity_match": False,
            "routed_team_match": False,
            "exact_label_match": False,
        }
    sentiment_match = output.sentiment_label.value == example.expected_sentiment
    category_match = output.category.value == example.expected_category
    severity_match = output.severity.value == example.expected_severity
    routed_team_match = output.routed_team == example.expected_routed_team
    return {
        "sentiment_match": sentiment_match,
        "category_match": category_match,
        "severity_match": severity_match,
        "routed_team_match": routed_team_match,
        "exact_label_match": all([sentiment_match, category_match, severity_match, routed_team_match]),
        "low_confidence": output.confidence_score < 0.5,
    }


def retrieval_metrics(example: EvaluationExampleSchema, results: Sequence[SearchResult], top_k: int) -> dict:
    relevant_ranks = [index for index, result in enumerate(results[:top_k], start=1) if _is_relevant(example, result)]
    expected_count = _expected_relevance_count(example)
    retrieved_count = len(results[:top_k])
    relevant_count = len(relevant_ranks)
    recalled_count = min(relevant_count, expected_count) if expected_count else 0
    return {
        "precision_at_k": relevant_count / retrieved_count if retrieved_count else 0.0,
        "recall_at_k": recalled_count / expected_count if expected_count else None,
        "hit_at_k": relevant_count > 0,
        "mrr": 1.0 / relevant_ranks[0] if relevant_ranks else 0.0,
        "average_retrieval_score": sum(result.score for result in results[:top_k]) / retrieved_count if retrieved_count else 0.0,
        "no_results": retrieved_count == 0,
        "retrieved_count": retrieved_count,
    }


def groundedness_check(
    example: EvaluationExampleSchema,
    output: StructuredAnalysisOutput | None,
    results: Sequence[SearchResult],
) -> dict:
    if not results:
        return {"status": GroundednessStatus.FAIL.value, "reason": "No retrieval evidence was found."}
    evidence_text = " ".join(result.text.lower() for result in results)
    keyword_hits = [keyword for keyword in example.expected_keywords if keyword.lower() in evidence_text]
    expected_titles = {title.lower() for title in example.expected_relevant_document_titles}
    title_hits = [
        title
        for title in expected_titles
        if any(str((result.metadata or {}).get("document_title", "")).lower() == title for result in results)
    ]
    retrieved_chunk_ids = {result.chunk_id for result in results if result.chunk_id is not None}
    cited_chunk_ids = set(output.evidence_chunk_ids if output is not None else [])
    expected_chunk_ids = set(example.expected_relevant_chunk_ids)
    cited_available_evidence = bool(cited_chunk_ids & retrieved_chunk_ids)
    expected_chunk_hit = bool(expected_chunk_ids & retrieved_chunk_ids) if expected_chunk_ids else False

    if cited_available_evidence or expected_chunk_hit or keyword_hits or title_hits:
        return {
            "status": GroundednessStatus.PASS.value,
            "reason": "Prediction has supporting retrieved evidence.",
            "keyword_hits": keyword_hits,
            "title_hits": title_hits,
        }
    return {
        "status": GroundednessStatus.WARN.value,
        "reason": "Retrieved evidence exists but did not match expected evidence signals.",
        "keyword_hits": keyword_hits,
        "title_hits": title_hits,
    }


def workflow_metrics(example: EvaluationExampleSchema, output: StructuredAnalysisOutput | None, low_confidence_threshold: float) -> dict:
    if output is None:
        return {"workflow_evaluated": False}
    predicted_escalate = output.severity.value in {"P0", "P1"} or (
        output.sentiment_label.value == "NEGATIVE" and output.category.value in {"PAYMENT", "SECURITY"}
    )
    predicted_needs_review = (
        output.severity.value in {"P0", "P1"}
        or output.confidence_score < low_confidence_threshold
        or not output.routed_team
    )
    metrics = {
        "workflow_evaluated": example.expected_escalate is not None or example.expected_needs_review is not None,
        "predicted_escalate": predicted_escalate,
        "predicted_needs_review": predicted_needs_review,
    }
    if example.expected_escalate is not None:
        metrics["escalation_match"] = predicted_escalate == example.expected_escalate
    if example.expected_needs_review is not None:
        metrics["review_match"] = predicted_needs_review == example.expected_needs_review
    return metrics


def aggregate_item_metrics(items: list[dict]) -> dict:
    total = len(items)
    if total == 0:
        return {}
    return {
        "sample_count": total,
        "analysis": {
            "sentiment_accuracy": _rate(items, "sentiment_match"),
            "category_accuracy": _rate(items, "category_match"),
            "severity_accuracy": _rate(items, "severity_match"),
            "routed_team_accuracy": _rate(items, "routed_team_match"),
            "exact_label_match_rate": _rate(items, "exact_label_match"),
            "invalid_output_rate": _rate(items, "invalid_output"),
            "low_confidence_rate": _rate(items, "low_confidence"),
            "provider_failure_rate": _rate(items, "provider_failed"),
        },
        "retrieval": {
            "precision_at_k": _average(items, "precision_at_k"),
            "recall_at_k": _average_present(items, "recall_at_k"),
            "hit_at_k": _rate(items, "hit_at_k"),
            "mrr": _average(items, "mrr"),
            "average_retrieval_score": _average(items, "average_retrieval_score"),
            "no_result_rate": _rate(items, "no_results"),
        },
        "groundedness": {
            "pass_rate": _rate_value(items, "groundedness_status", GroundednessStatus.PASS.value),
            "warn_rate": _rate_value(items, "groundedness_status", GroundednessStatus.WARN.value),
            "fail_rate": _rate_value(items, "groundedness_status", GroundednessStatus.FAIL.value),
        },
        "workflow": {
            "escalation_accuracy": _average_present(items, "escalation_match"),
            "review_accuracy": _average_present(items, "review_match"),
        },
        "latency": latency_summary([item.get("total_latency_ms") for item in items if item.get("total_latency_ms") is not None]),
        "failures": {
            "failed_items": sum(1 for item in items if item.get("error_code")),
        },
    }


def latency_summary(values: Sequence[int | float]) -> dict:
    if not values:
        return {"count": 0, "p50_ms": None, "p95_ms": None, "p99_ms": None, "avg_ms": None}
    sorted_values = sorted(float(value) for value in values)
    return {
        "count": len(sorted_values),
        "p50_ms": _percentile(sorted_values, 50),
        "p95_ms": _percentile(sorted_values, 95),
        "p99_ms": _percentile(sorted_values, 99),
        "avg_ms": sum(sorted_values) / len(sorted_values),
    }


def _is_relevant(example: EvaluationExampleSchema, result: SearchResult) -> bool:
    if result.chunk_id is not None and result.chunk_id in set(example.expected_relevant_chunk_ids):
        return True
    metadata = result.metadata or {}
    document_title = str(metadata.get("document_title", "")).lower()
    if document_title and document_title in {title.lower() for title in example.expected_relevant_document_titles}:
        return True
    text = result.text.lower()
    return any(keyword.lower() in text for keyword in example.expected_keywords)


def _expected_relevance_count(example: EvaluationExampleSchema) -> int:
    if example.expected_relevant_chunk_ids:
        return len(set(example.expected_relevant_chunk_ids))
    if example.expected_relevant_document_titles:
        return len(set(example.expected_relevant_document_titles))
    if example.expected_keywords:
        return 1
    return 0


def _rate(items: list[dict], key: str) -> float:
    return sum(1 for item in items if item.get(key) is True) / len(items)


def _rate_value(items: list[dict], key: str, value: str) -> float:
    return sum(1 for item in items if item.get(key) == value) / len(items)


def _average(items: list[dict], key: str) -> float:
    values = [float(item[key]) for item in items if item.get(key) is not None]
    return sum(values) / len(values) if values else 0.0


def _average_present(items: list[dict], key: str) -> float | None:
    values = [item[key] for item in items if item.get(key) is not None]
    if not values:
        return None
    return sum(1 for value in values if value is True) / len(values) if isinstance(values[0], bool) else sum(values) / len(values)


def _percentile(sorted_values: list[float], percentile: int) -> float:
    if len(sorted_values) == 1:
        return sorted_values[0]
    index = (len(sorted_values) - 1) * percentile / 100
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = index - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight
