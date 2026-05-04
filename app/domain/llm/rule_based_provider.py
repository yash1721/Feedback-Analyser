from app.domain.analysis.prompts import AnalysisPrompt
from app.domain.llm.fake_provider import _extract_chunk_ids
from app.domain.llm.provider import LLMProviderResponse


class RuleBasedAnalysisProvider:
    provider_name = "rule_based"

    def __init__(self, model_name: str = "rule-based-feedback-analyzer-v1") -> None:
        self.model_name = model_name

    def analyze_feedback(self, prompt: AnalysisPrompt) -> LLMProviderResponse:
        text = prompt.feedback_text.lower()
        evidence_chunk_ids = _extract_chunk_ids(prompt.evidence_context)
        category, routed_team = self._category_and_team(text)
        severity = self._severity(text)
        sentiment_label = "NEGATIVE" if any(word in text for word in ["fail", "failed", "broken", "delay", "error", "issue"]) else "NEUTRAL"
        confidence = 0.78 if evidence_chunk_ids else 0.45
        return LLMProviderResponse(
            provider=self.provider_name,
            model_name=self.model_name,
            raw_output={
                "sentiment_label": sentiment_label,
                "sentiment_score": confidence if sentiment_label == "NEGATIVE" else 0.55,
                "category": category,
                "severity": severity,
                "routed_team": routed_team,
                "summary": self._summary(category, severity),
                "recommended_action": self._action(category, routed_team),
                "confidence_score": confidence,
                "reasoning_summary": "Rule-based analysis used feedback keywords and retrieved evidence availability.",
                "evidence_chunk_ids": evidence_chunk_ids,
            },
        )

    def _category_and_team(self, text: str) -> tuple[str, str]:
        if any(word in text for word in ["payment", "checkout", "transaction", "refund"]):
            return "PAYMENT", "Payment Team"
        if any(word in text for word in ["delivery", "shipping", "shipment"]):
            return "DELIVERY", "Logistics Team"
        if any(word in text for word in ["ui", "screen", "button", "design"]):
            return "UI", "Frontend Team"
        if any(word in text for word in ["slow", "latency", "timeout", "performance"]):
            return "PERFORMANCE", "Backend Team"
        if any(word in text for word in ["security", "fraud", "breach"]):
            return "SECURITY", "Backend Team"
        if any(word in text for word in ["support", "ticket", "agent"]):
            return "SUPPORT", "Customer Support Team"
        return "OTHER", "Customer Support Team"

    def _severity(self, text: str) -> str:
        if any(word in text for word in ["outage", "breach", "data loss", "cannot use"]):
            return "P0"
        if any(word in text for word in ["failed", "blocked", "urgent", "fraud"]):
            return "P1"
        if any(word in text for word in ["delay", "slow", "issue", "error"]):
            return "P2"
        return "P3"

    def _summary(self, category: str, severity: str) -> str:
        return f"Feedback indicates a {category.lower()} concern with {severity} severity."

    def _action(self, category: str, routed_team: str) -> str:
        return f"Route to {routed_team} to investigate the {category.lower()} issue and follow up with the customer."
