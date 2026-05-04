import pytest

from app.domain.analysis.output_parser import AnalysisOutputParseError, parse_structured_analysis


def test_parse_structured_analysis_accepts_valid_json():
    output = parse_structured_analysis(
        {
            "sentiment_label": "NEGATIVE",
            "sentiment_score": 0.9,
            "category": "PAYMENT",
            "severity": "P1",
            "routed_team": "Payment Team",
            "summary": "Payment failed.",
            "recommended_action": "Investigate checkout payments.",
            "confidence_score": 0.8,
            "reasoning_summary": "Payment evidence was present.",
            "evidence_chunk_ids": [1],
        }
    )

    assert output.category == "PAYMENT"
    assert output.evidence_chunk_ids == [1]


def test_parse_structured_analysis_rejects_invalid_json():
    with pytest.raises(AnalysisOutputParseError):
        parse_structured_analysis("{not json")


def test_parse_structured_analysis_rejects_invalid_schema():
    with pytest.raises(AnalysisOutputParseError):
        parse_structured_analysis({"sentiment_label": "UNKNOWN"})
