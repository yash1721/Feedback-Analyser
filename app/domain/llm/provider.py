from dataclasses import dataclass
from typing import Protocol

from app.domain.analysis.prompts import AnalysisPrompt


@dataclass(frozen=True)
class LLMProviderResponse:
    provider: str
    model_name: str
    raw_output: str | dict


class LLMProvider(Protocol):
    provider_name: str
    model_name: str

    def analyze_feedback(self, prompt: AnalysisPrompt) -> LLMProviderResponse:
        """Analyze feedback and return raw provider output."""
