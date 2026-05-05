import re
from dataclasses import dataclass
from enum import StrEnum


class PromptInjectionRisk(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True)
class PromptInjectionResult:
    detected: bool
    risk_level: PromptInjectionRisk
    matched_patterns: list[str]


class PromptInjectionDetector:
    PATTERNS: list[tuple[str, PromptInjectionRisk]] = [
        (r"ignore (all )?(previous|prior) instructions", PromptInjectionRisk.HIGH),
        (r"reveal (the )?(system|developer) prompt", PromptInjectionRisk.HIGH),
        (r"print (the )?(secrets|api keys|credentials)", PromptInjectionRisk.HIGH),
        (r"exfiltrate", PromptInjectionRisk.HIGH),
        (r"do not follow (the )?(rules|policy)", PromptInjectionRisk.MEDIUM),
        (r"override (the )?(policy|instructions)", PromptInjectionRisk.MEDIUM),
        (r"act as (a )?(developer|system|admin)", PromptInjectionRisk.MEDIUM),
        (r"system prompt", PromptInjectionRisk.MEDIUM),
    ]

    def detect(self, text: str | None) -> PromptInjectionResult:
        value = (text or "").lower()
        matched: list[str] = []
        highest = PromptInjectionRisk.LOW
        for pattern, risk in self.PATTERNS:
            if re.search(pattern, value):
                matched.append(pattern)
                if risk == PromptInjectionRisk.HIGH:
                    highest = PromptInjectionRisk.HIGH
                elif highest != PromptInjectionRisk.HIGH:
                    highest = PromptInjectionRisk.MEDIUM
        return PromptInjectionResult(detected=bool(matched), risk_level=highest, matched_patterns=matched)
