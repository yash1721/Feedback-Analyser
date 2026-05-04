from app.domain.analysis.prompts import AnalysisPrompt
from app.domain.llm.provider import LLMProviderResponse


class FakeLLMProvider:
    provider_name = "fake"

    def __init__(self, model_name: str = "fake-feedback-analyzer") -> None:
        self.model_name = model_name

    def analyze_feedback(self, prompt: AnalysisPrompt) -> LLMProviderResponse:
        return LLMProviderResponse(
            provider=self.provider_name,
            model_name=self.model_name,
            raw_output={
                "sentiment_label": "NEGATIVE",
                "sentiment_score": 0.9,
                "category": "PAYMENT",
                "severity": "P2",
                "routed_team": "Payment Team",
                "summary": "The customer reported a payment issue.",
                "recommended_action": "Review checkout payment logs and follow up with the customer.",
                "confidence_score": 0.85,
                "reasoning_summary": "The feedback and evidence mention payment failure.",
                "evidence_chunk_ids": _extract_chunk_ids(prompt.evidence_context),
            },
        )


def _extract_chunk_ids(evidence_context: str) -> list[int]:
    chunk_ids: list[int] = []
    for part in evidence_context.split("chunk_id=")[1:]:
        value = part.split(maxsplit=1)[0]
        if value.isdigit():
            chunk_ids.append(int(value))
    return chunk_ids
