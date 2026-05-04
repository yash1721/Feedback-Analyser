from app.domain.analysis.prompts import build_feedback_analysis_prompt
from app.domain.llm.fake_provider import FakeLLMProvider
from app.domain.llm.rule_based_provider import RuleBasedAnalysisProvider
from app.domain.retrieval.vector_store import SearchResult


def test_fake_provider_returns_deterministic_output():
    prompt = build_feedback_analysis_prompt(
        feedback_text="Payment failed.",
        evidence=[SearchResult(text="Payment context", score=0.9, chunk_id=7)],
        prompt_version="test",
    )

    response = FakeLLMProvider().analyze_feedback(prompt)

    assert response.provider == "fake"
    assert response.raw_output["category"] == "PAYMENT"
    assert response.raw_output["evidence_chunk_ids"] == [7]


def test_rule_based_provider_routes_payment_feedback():
    prompt = build_feedback_analysis_prompt(
        feedback_text="Customer had checkout payment failure.",
        evidence=[SearchResult(text="Payment context", score=0.9, chunk_id=3)],
        prompt_version="test",
    )

    response = RuleBasedAnalysisProvider().analyze_feedback(prompt)

    assert response.raw_output["category"] == "PAYMENT"
    assert response.raw_output["routed_team"] == "Payment Team"
    assert response.raw_output["confidence_score"] > 0.5
