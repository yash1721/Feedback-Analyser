from dataclasses import dataclass

from app.domain.analysis.schemas import StructuredAnalysisOutput
from app.domain.guardrails.pii_redaction import PIIRedactionService


@dataclass(frozen=True)
class OutputGuardrailResult:
    allowed: bool
    reason: str | None = None


class OutputGuardrailService:
    FORBIDDEN_TERMS = ["api key", "password", "secret", "credential", "exfiltrate", "reveal system prompt"]

    def __init__(self, pii_service: PIIRedactionService | None = None) -> None:
        self.pii_service = pii_service or PIIRedactionService()

    def validate(self, output: StructuredAnalysisOutput) -> OutputGuardrailResult:
        combined = " ".join([output.summary, output.recommended_action, output.reasoning_summary]).lower()
        for term in self.FORBIDDEN_TERMS:
            if term in combined:
                return OutputGuardrailResult(False, f"Output contains forbidden term: {term}")
        pii_result = self.pii_service.redact(" ".join([output.summary, output.recommended_action, output.reasoning_summary]))
        if pii_result.detected:
            return OutputGuardrailResult(False, "Output contains PII-like content.")
        return OutputGuardrailResult(True)
